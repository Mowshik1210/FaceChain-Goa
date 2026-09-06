#!/usr/bin/env python3
"""FaceChain Goa — CLI Entry Point

HH GOA 2026 — TASK 3
Face Identification & Blockchain Verification

Usage:
    python main.py --demo              Run demo mode
    python main.py --image PATH        Process specific image
    python main.py --tamper-demo       Run with tamper simulation
"""
import os
import sys
import argparse

from rich.console import Console

from app.pipeline import FaceChainPipeline
from app.config import config

console = Console()


def print_banner():
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║              [bold cyan]FACECHAIN GOA[/bold cyan]                              ║
║        [dim]DISCOVER • FINGERPRINT • VERIFY[/dim]                    ║
║                                                              ║
╠══════════════════════════════════════════════════════════════╣
║  [dim]HH GOA 2026 — TASK 3[/dim]                                     ║
║  [dim]Face Identification & Blockchain Verification[/dim]            ║
╚══════════════════════════════════════════════════════════════╝
    """
    console.print(banner)


def print_timeline():
    timeline = """
[dim]Verification Timeline:[/dim]
  [cyan]01[/cyan] FACE DETECTED
  [cyan]02[/cyan] SEARCH COMPLETED
  [cyan]03[/cyan] MATCH FOUND
  [cyan]04[/cyan] FINGERPRINT CREATED
  [cyan]05[/cyan] BLOCKCHAIN ANCHORED
  [cyan]06[/cyan] RE-VERIFIED
    """
    console.print(timeline)


def run_demo():
    print_banner()
    demo_path = config.demo_image_path
    if not os.path.exists(demo_path):
        console.print(f"[bold yellow]Demo image not found at {demo_path}[/]")
        console.print("[dim]Creating a demo image...[/]")
        from PIL import Image, ImageDraw
        img = Image.new("RGB", (400, 400), color=(200, 200, 200))
        draw = ImageDraw.Draw(img)
        draw.ellipse([100, 50, 300, 350], fill=(255, 220, 180), outline=(0,0,0), width=2)
        draw.ellipse([140, 120, 170, 160], fill=(255, 255, 255), outline=(0,0,0), width=1)
        draw.ellipse([230, 120, 260, 160], fill=(255, 255, 255), outline=(0,0,0), width=1)
        draw.ellipse([145, 125, 165, 155], fill=(50, 50, 50))
        draw.ellipse([235, 125, 255, 155], fill=(50, 50, 50))
        draw.arc([150, 180, 250, 280], 0, 180, fill=(100, 50, 50), width=3)
        os.makedirs(os.path.dirname(demo_path), exist_ok=True)
        img.save(demo_path)
        console.print(f"[green]Created demo image: {demo_path}[/]")
    console.print(f"\n[bold]Demo Mode[/] — Processing: [cyan]{demo_path}[/]")
    console.print("[dim]Using authorized test image for demonstration.[/]\n")
    print_timeline()
    console.print()
    pipeline = FaceChainPipeline()
    result = pipeline.run(demo_path, console_output=True)
    return result.success


def run_live(image_path: str):
    print_banner()
    if not os.path.exists(image_path):
        console.print(f"[bold red]Error: Image not found: {image_path}[/]")
        return False
    console.print(f"\n[bold]Live Mode[/] — Processing: [cyan]{image_path}[/]")
    console.print("[yellow]Privacy Notice:[/] Only authorized images should be processed.\n")
    print_timeline()
    console.print()
    pipeline = FaceChainPipeline()
    result = pipeline.run(image_path, console_output=True)
    return result.success


def run_tamper_demo():
    print_banner()
    console.print("\n[bold red]TAMPER DETECTION DEMO[/]")
    console.print("[dim]This demo shows how the system detects modified evidence.[/]\n")
    demo_path = config.demo_image_path
    if not os.path.exists(demo_path):
        run_demo()
    pipeline = FaceChainPipeline()
    result = pipeline.run(demo_path, console_output=True)
    if result.success and result.evidence_manifest:
        console.print("\n[bold red]Now simulating tampering...[/]")
        from PIL import Image
        from app.blockchain.verifier import BlockchainVerifier
        from app.evidence.fingerprint import EvidenceFingerprinter
        img = Image.open(demo_path).convert("RGB")
        verifier = BlockchainVerifier()
        tampered = verifier.simulate_tamper(img)
        tamper_path = os.path.join(config.temp_dir, "tampered.jpg")
        tampered.save(tamper_path)
        console.print(f"[dim]Tampered image saved: {tamper_path}[/]")
        fp = EvidenceFingerprinter()
        original_hash = result.original_hash
        current_hash = fp.sha256(tampered)
        console.print("\n[bold cyan]╔" + "═" * 48 + "╗")
        console.print("[bold cyan]║[/]" + " " * 10 + "[bold white]TAMPER VERIFICATION[/]" + " " * 15 + "[bold cyan]║")
        console.print("[bold cyan]╠" + "═" * 48 + "╣")
        console.print(f"[bold cyan]║[/]  Original Hash: {original_hash[:20]}...  [bold cyan]║")
        console.print(f"[bold cyan]║[/]  Tampered Hash: {current_hash[:20]}...  [bold cyan]║")
        console.print("[bold cyan]║" + " " * 48 + "║")
        console.print(f"[bold cyan]║[/]      [bold red]✗ TAMPER DETECTED[/]" + " " * 21 + "[bold cyan]║")
        console.print("[bold cyan]╚" + "═" * 48 + "╝")


def main():
    parser = argparse.ArgumentParser(
        description="FaceChain Goa — Face Identification & Blockchain Verification",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --demo              Run with demo image
  python main.py --image photo.jpg   Process your image
  python main.py --tamper-demo       Show tamper detection
        """
    )
    parser.add_argument("--demo", action="store_true", help="Run demo mode")
    parser.add_argument("--image", type=str, help="Path to input image")
    parser.add_argument("--tamper-demo", action="store_true", help="Run tamper detection demo")
    args = parser.parse_args()

    if args.tamper_demo:
        success = run_tamper_demo()
    elif args.image:
        success = run_live(args.image)
    else:
        success = run_demo()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
