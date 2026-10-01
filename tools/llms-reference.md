## Quick reference

Enough to write a handler correctly. The pages under Docs give the full rules.

```go
type CreateOrder struct {
    Paging                                    // embedded struct: its fields are promoted
    TeamID  uuid.UUID         `path:"team"`    // mux pattern "POST /teams/{team}/orders"
    DryRun  bool              `query:"dry_run"`
    Tags    []string          `query:"tag"`    // ?tag=a&tag=b; never split on commas
    Page    int               `form:"page"`    // form body page=2, or else ?page=2
    Filter  map[string]string `query:"filter"` // ?filter[status]=open&filter[team]=core
    Email   string            `body:"email,required"`
    Note    *string           `body:"note"`    // nil: not sent, sent as null, or failed
    Items   []Item            `body:"items"`   // nested structs bind by their body/json tags
    Trace   string            `header:"X-Request-ID"`
    Session string            `cookie:"session"`
}

// Optional. Runs only once every field has bound, with r.Context().
func (r CreateOrder) Validate(ctx context.Context) error { return nil }

var req CreateOrder
err := binder.Bind(r, &req) // or binder.BindWithOptions(r, &req, binder.BindOptions{...})
```

### Tags

- `path:"name"` reads `r.PathValue`, which `http.ServeMux` patterns such as `/users/{id}` fill, as does any router that calls `r.SetPathValue`.
- `query:"name"`, `cookie:"name"`, and `header:"Name"`, which matches case-insensitively.
- `body:"name"` reads the body as JSON (any JSON media type, `+json` included), `application/x-www-form-urlencoded` or `multipart/form-data`, chosen by `Content-Type`. A body of any other type is not parsed.
- `json:"name"` means the same as `body:`. Keep it for types shared with `encoding/json`. Names match exactly, not case-insensitively.
- `form:"name"` reads as `r.FormValue` and Gin's `form` tag do: the form body's value (urlencoded or multipart, files included) when the body has the key, and otherwise the query's. A JSON body is not a form, so on a JSON request it reads the query alone.
- When a field has several of these tags, the first in the order path, query, body, json, cookie, header, form wins. An empty name, as in `query:",required"`, binds under the Go field name.

### Options

binder has two options, written after the name:
- `required`: a missing value is a failure wrapping `ErrMissingRequired`. For path, query and header an empty value counts as missing. A body key or cookie that is present but empty satisfies it.
- `omitempty`: a present but empty value leaves the field as it was. In JSON, empty means `""`, `0`, `false`, `null`, `{}` or `[]`; from other sources it means `""`. It has no effect on pointers.

binder has no validation tags; put rules in `Validate(ctx)`. An absent value never touches its field, so set defaults on the struct before calling `Bind`.

### Types

binder can fill:
- `string`, `bool`, and every integer and float kind (overflow is an error);
- `time.Duration` as text such as `"5s"` (a JSON number is nanoseconds);
- any `encoding.TextUnmarshaler`, such as `time.Time`, `uuid.UUID` or `netip.Addr`;
- any type with its own `UnmarshalJSON`, from a JSON body (`json.RawMessage` is kept as sent);
- slices, maps, nested structs and embedded structs;
- pointers to any of these;
- `*multipart.FileHeader` and `[]*multipart.FileHeader` for uploads.

Fixed-size arrays are not supported; use slices.

Rules for collections and pointers:
- **Slices** take repeated values. A single value binds as a one-element slice.
- **Maps** bind from a JSON object, or from `name[key]=value` pairs in a query or form. Only one level of brackets is read. Keys convert to the map's key type.
- **Pointers** are nil unless a value bound through them, so a pointer tells "not sent" from "sent as zero", as a PATCH needs.

### Errors

```go
if err := binder.Bind(r, &req); err != nil {
    var errs binder.BindErrors
    var invalid ValidationErrors // whatever type your Validate returns
    switch {
    case errors.As(err, &errs):
        // 400. Every failed field, in field order: e.Name is the client's key,
        // such as "items[2].qty", and e.Source is where it came from.
        // errors.Is(e, binder.ErrMissingRequired) marks a missing required value.
    case errors.As(err, &invalid):
        // 422. Your Validate's error, which Bind wraps with %w.
    case errors.Is(err, binder.ErrBodyTooLarge):
        // 413
    case errors.Is(err, binder.ErrInvalidTarget):
        // 500. A bug in the request type, not the client's fault.
    default:
        // 400. ErrMalformedBody, or a body that could not be read.
    }
    return
}
```

- Word client messages from `Name`, `Source` and the sentinel an entry wraps. `Message` names Go fields.
- With `DisallowUnknownFields: true`, each body key that no field binds is an entry wrapping `ErrUnknownField`.
- The body limit is 10 MB (`DefaultMaxBodySize`). An upload is held in memory, so raise `MaxBodySize` deliberately on an upload endpoint.
- `Bind` reads the body and puts it back, so later code can still read `r.Body`.

### Mistakes to avoid

- Don't use `uri:`, `param:` or `binding:"required"`. Those are Gin's and Echo's tags: binding refuses a type that has them with `ErrInvalidTarget`. Use `path:` and `,required`, and put other rules in `Validate`. (`form:` is supported, as described above.)
- A `validate:"..."` tag is not read by binder. Keep it only if your `Validate` method passes the struct to a validation library.
- Don't write `json:"x,required"`. It works, but linters flag the unknown option; use `body:"x,required"`.
- Don't act on the struct once `Bind` has returned an error. Fields that failed can hold part of a value.
