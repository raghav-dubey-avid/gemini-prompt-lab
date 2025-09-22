from __future__ import annotations
import pathlib
import typer
from rich.console import Console
from typing import Optional

from .genai_client import GeminiClient

app = typer.Typer(no_args_is_help=True)
console = Console()

def _read_if_path(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    p = pathlib.Path(s)
    return p.read_text(encoding="utf-8") if p.exists() else s

@app.command()
def run(
    prompt: Optional[str] = typer.Option(
        None, help="Prompt text OR a path to a .txt file"
    ),
    system: Optional[str] = typer.Option(
        None, help="Path to a system.md (optional)"
    ),
    model: Optional[str] = typer.Option(
        None, help="Model ID (default comes from the wrapper)"
    ),
    temp: float = typer.Option(0.7, help="Sampling temperature"),
    max_tokens: int = typer.Option(512, help="Max output tokens"),
    show_tokens: bool = typer.Option(False, help="Print token count before generation"),
):
    """
    Generate a single response using the official google-genai client.
    """
    prompt_text = _read_if_path(prompt)
    if not prompt_text:
        raise typer.BadParameter("Provide --prompt with text or a .txt path")

    system_text = None
    if system:
        p = pathlib.Path(system)
        if not p.exists():
            raise typer.BadParameter(f"System file not found: {system}")
        system_text = p.read_text(encoding="utf-8")

    client = GeminiClient(model=model or None)

    if show_tokens:
        tokens = client.count_tokens(prompt_text)
        console.print(f"[dim]Prompt tokens: {tokens}[/dim]")

    resp = client.generate_text(
        prompt_text,
        system_instruction=system_text,
        temperature=temp,
        max_output_tokens=max_tokens,
    )

    console.rule("[bold]MODEL OUTPUT")
    console.print(resp.text)

@app.command()
def tokens(
    prompt: str = typer.Argument(..., help="Prompt text OR path to a .txt file")
):
    """
    Count tokens for a prompt (useful for budgeting).
    """
    prompt_text = _read_if_path(prompt)
    if not prompt_text:
        raise typer.BadParameter("Give prompt text or a .txt path")
    client = GeminiClient()
    total = client.count_tokens(prompt_text)
    console.print(f"Total tokens: {total}")

if __name__ == "__main__":
    app()
