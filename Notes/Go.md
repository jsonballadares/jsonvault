status:: #fleeting
tags:: #programming, #reference

---
# Go

## Resources

- https://app.pluralsight.com/paths/skill/go
- https://go.dev/doc/effective_go
- https://go.dev/doc/
- https://go.dev/play/
- https://pkg.go.dev
- https://go.dev/blog/
- https://go.dev/wiki/
- https://go.dev/learn/
- https://pkg.go.dev/builtin
- https://lets-go-further.alexedwards.net/
- https://interpreterbook.com/
- https://100go.co/
- https://quii.gitbook.io/learn-go-with-tests
- https://github.com/golang-standards/project-layout

## Concepts

Go is often described as C for the 21st century.

**Statically typed** — the compiler determines and enforces all variable and expression types at compile time, even when using type inference and interfaces.

**Strongly typed** — requires explicit conversions, forbids implicit coercion, and enforces exact type compatibility across all operations.

**Compilation** — the fast, deterministic process of turning statically and strongly typed source code into a single native executable with all dependencies embedded. Go avoids headers, implicit dependencies, and complex preprocessing, allowing large codebases to build in seconds.

**Concurrency model** — uses lightweight goroutines and channels to make concurrent programs simple, scalable, and efficient.

**Simplicity** — small language surface, built-in garbage collection, and clear conventions reduce incidental complexity.

## Project Structure

A Go project is composed of two things:

**Modules** — the outer boundary, defined by `go.mod`. Represents one dependency version and maps to a VCS repo. A module can contain many packages.

```
my-service/
├── go.mod
├── go.sum
├── main.go
└── internal/
```

**Packages** — the unit that actually compiles. A package is a directory of `.go` files sharing one namespace and one compilation unit.

```
auth/
├── handler.go
├── service.go
└── repo.go
```

---
# References

- [[Concurrency In Go]]
- [[Go Strings Bytes and Runes]]
