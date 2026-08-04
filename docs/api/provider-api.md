# DOBO CAD Kernel

# Provider API Specification

Version: 2.0

---

# 1. Purpose

This document defines the official Provider API of the DOBO CAD Kernel.

Providers are responsible for generating reusable two-dimensional geometry.

Every geometric source supported by the Kernel shall implement this API.

Examples include:

- Circle Provider
- Polygon Provider
- SVG Provider
- Text Provider
- DXF Provider
- QR Provider
- Voronoi Provider

The objective is to guarantee that every Provider can be integrated into the Kernel without modifying existing code.

---

# 2. Responsibilities

A Provider has exactly one responsibility:

Generate Contours.

A Provider never:

- creates solids;
- performs boolean operations;
- places geometry on surfaces;
- exports files;
- modifies the current Model.

---

# 3. Provider Lifecycle

Every Provider follows the same execution sequence.

```
Create Provider

↓

Validate Request

↓

Generate Contours

↓

Return Contours

↓

Finish
```

The Provider owns no state after execution.

---

# 4. Public Interface

Every Provider shall expose the following interface.

```python
class Provider(ABC):

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique provider name."""

    @abstractmethod
    def validate(
        self,
        request: ProviderRequest,
    ) -> None:
        """Validate input parameters."""

    @abstractmethod
    def build_contours(
        self,
        request: ProviderRequest,
    ) -> ContourSet:
        """Generate contour geometry."""
```

This interface defines the minimum contract required by the Kernel.

---

# 5. ProviderRequest

Every Provider receives a ProviderRequest.

A ProviderRequest contains:

- provider identifier;
- parameters;
- metadata.

The request object is immutable.

Providers must never modify the request.

---

# 6. Output

The output of every Provider is a collection of Contours.

```
Provider

↓

Contour[]

↓

Pipeline
```

No Provider may return CAD solids.

---

# 7. Validation

Providers are responsible for validating their own parameters.

Examples:

Circle Provider

- radius > 0

Polygon Provider

- sides >= 3

SVG Provider

- file exists

Text Provider

- non-empty string

Providers shall raise descriptive exceptions whenever validation fails.

---

# 8. Error Handling

Providers never terminate the Kernel.

Failures are reported by raising exceptions.

The Pipeline decides how execution continues.

---

# 9. Registration

Every Provider must register itself through the Provider Registry.

Example:

```python
register_provider(
    "circle",
    CircleProvider,
)
```

The Kernel never instantiates Providers directly.

Instantiation is delegated to the Registry.

---

# 10. Stateless Design

Providers should be stateless.

A Provider should not store:

- execution history;
- generated geometry;
- references to the Model;
- references to other Providers.

Every execution should be independent.

---

# 11. Dependencies

Providers may depend on:

- geometry utilities;
- mathematical utilities;
- parsing libraries.

Providers must never depend on:

- Surface Engine;
- Extrusion Engine;
- Boolean Engine;
- Export Engine.

---

# 12. Examples

Examples of valid Providers:

Circle Provider

Produces one circular contour.

Polygon Provider

Produces one polygon contour.

SVG Provider

Produces one or more contours parsed from an SVG file.

Text Provider

Produces one contour set per glyph.

QR Provider

Produces one contour per filled QR module.

---

# 13. Design Rules

Rule 1

One Provider, one responsibility.

Rule 2

Providers generate Contours only.

Rule 3

Providers are reusable.

Rule 4

Providers are stateless.

Rule 5

Providers communicate only through contracts.

Rule 6

Providers are independently testable.

---

# 14. Future Compatibility

New Providers shall integrate into the Kernel by implementing this interface.

No architectural changes should be required.

---

# 15. Summary

The Provider API defines the standard interface for every geometry source supported by the DOBO CAD Kernel.

By enforcing a single contract, the Kernel guarantees consistency, extensibility and long-term maintainability.