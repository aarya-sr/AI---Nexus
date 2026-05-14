from pydantic import BaseModel


class ToolSchema(BaseModel):
    id: str
    name: str
    description: str
    category: str
    accepts: list[str]
    outputs: list[str]
    output_format: str
    limitations: list[str]
    dependencies: list[str]
    code_template: str
    compatible_with: list[str] = []
    incompatible_with: list[str] = []
