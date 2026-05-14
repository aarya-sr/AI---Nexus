from pydantic import BaseModel


class CodeBundle(BaseModel):
    files: dict[str, str]
    framework: str
    entry_point: str = "main.py"
    dependencies: list[str] = []
    validation_passed: bool = False
    validation_errors: list[str] = []
