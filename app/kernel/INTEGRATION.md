# DOBO advanced geometry bundle

This bundle adds the implementation files for:

- Revolve through `GeometryRequest`
- Loft through `GeometryRequest`
- Sweep through `GeometryRequest`
- Shell as a Kernel operation over an existing Solid

## Important

This package was produced from the public `main` contracts visible in GitHub.
It was not compiled against Walter's current local working tree, because that
tree is on `E:\dobo-engine` and is not mounted in the artifact environment.

Apply the files, then perform the small integration edits below.

## 1. Add SHELL to OperationType

In `app/kernel/contracts/operations/base_operation.py`, add:

```python
SHELL = "shell"
```

to `OperationType`.

## 2. Export ShellOperation

In `app/kernel/contracts/operations/__init__.py`:

```python
from .shell_operation import ShellOperation
```

and add `"ShellOperation"` to `__all__`.

## 3. Export/register executors

In `app/kernel/geometry/__init__.py`, export:

```python
from .revolve_request_executor import RevolveRequestExecutor
from .loft_request_executor import LoftRequestExecutor
from .sweep_request_executor import SweepRequestExecutor
```

In `app/testing/kernel_builders.py`, after registering `ExtrudeRequestExecutor`:

```python
registry.register(RevolveRequestExecutor())
registry.register(LoftRequestExecutor())
registry.register(SweepRequestExecutor())
```

In the operation dispatcher factory, register:

```python
dispatcher.register(ShellOperationExecutor())
```

## 4. CadQuery compatibility check

CadQuery method signatures can vary by installed release. Run:

```powershell
python -c "import cadquery as cq, inspect; print(inspect.signature(cq.Solid.revolve)); print(inspect.signature(cq.Solid.makeLoft)); print(inspect.signature(cq.Solid.sweep))"
```

If signatures differ, adjust only the executor call sites.

## 5. Compile

```powershell
python -m py_compile app\kernel\geometry\revolve_request_executor.py
python -m py_compile app\kernel\geometry\loft_request_executor.py
python -m py_compile app\kernel\geometry\sweep_request_executor.py
python -m py_compile app\kernel\contracts\operations\shell_operation.py
python -m py_compile app\kernel\core\shell_operation_executor.py
```

## 6. Suggested commit

```powershell
git add app\kernel INTEGRATION.md
git commit -m "feat(kernel): add revolve loft sweep and shell operations"
git push origin main
```
