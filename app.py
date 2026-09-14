from contextlib import asynccontextmanager
from importlib import import_module
from pathlib import Path

from fastapi import FastAPI

TOOLS_DIR = Path(__file__).parent / "tools"


def discover_tools():
    """
    Discover tool modules inside the tools/ directory.

    Each tool module can expose:
        register(app)
    or:
        register(mcp)
    depending on how the tool is implemented.
    """
    discovered = []

    if not TOOLS_DIR.exists():
        return discovered

    for file in sorted(TOOLS_DIR.glob("*.py")):
        if file.name.startswith("_"):
            continue

        module_name = f"tools.{file.stem}"

        try:
            module = import_module(module_name)

            if hasattr(module, "TOOL_METADATA"):
                discovered.append({
                    "module": module_name,
                    **module.TOOL_METADATA,
                })
            else:
                discovered.append({
                    "module": module_name,
                    "name": file.stem,
                })

        except Exception as exc:
            discovered.append({
                "module": module_name,
                "name": file.stem,
                "status": "error",
                "error": str(exc),
            })

    return discovered


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application startup/shutdown lifecycle.
    """
    app.state.tools = discover_tools()
    yield


app = FastAPI(
    title="NORA Tools",
    description="Tool infrastructure for NORA Earth Intelligence.",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/")
async def root():
    return {
        "name": "NORA Tools",
        "status": "online",
        "version": app.version,
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "nora-tools",
    }


@app.get("/tools")
async def list_tools():
    """
    Return the tools currently discovered by NORA Tools.
    """
    return {
        "count": len(app.state.tools),
        "tools": app.state.tools,
    }


@app.get("/tools/{tool_name}")
async def get_tool(tool_name: str):
    """
    Return metadata for a specific discovered tool.
    """
    for tool in app.state.tools:
        if tool.get("name") == tool_name:
            return tool

    return {
        "error": "Tool not found",
        "tool": tool_name,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
