"""
Wrapper para o binário pdf2htmlEX: converte PDF em HTML preservando layout e fontes.

Requer uma das opções:
  - pdf2htmlEX instalado no sistema (apt em versões antigas; em Ubuntu 24/25 muitas vezes não existe).
  - Docker: usa a imagem bwits/pdf2htmlex quando o binário não está disponível.

Uso na VPS (Ubuntu 25): instale Docker e execute o script; o código usa Docker automaticamente.
  sudo apt install docker.io
  sudo docker pull bwits/pdf2htmlex
"""
from pathlib import Path
import shutil
import subprocess
import re

# Imagens Docker (tenta a primeira que existir localmente; usar tag explícita pode evitar erros de manifest)
# Nota: bwits/pdf2htmlex usa formato antigo e falha em Docker recente; pdf2htmlex/pdf2htmlex:latest não existe.
# Experimentar: sudo docker pull mindspacephx/docker-pdf2htmlex:1.0.3  ou  sergiomtzlosa/pdf2htmlex
PDF2HTMLEX_DOCKER_IMAGES = [
    "mindspacephx/docker-pdf2htmlex:1.0.3",
    "sergiomtzlosa/pdf2htmlex",
    "bwits/pdf2htmlex",
]


def _find_binary() -> str | None:
    """Retorna o caminho do binário pdf2htmlEX se existir."""
    for name in ("pdf2htmlEX", "pdf2htmlex"):
        path = shutil.which(name)
        if path:
            return path
    return None


def _imagem_docker_disponivel() -> str | None:
    """Retorna o nome da primeira imagem Docker disponível, ou None."""
    if not shutil.which("docker"):
        return None
    for image in PDF2HTMLEX_DOCKER_IMAGES:
        try:
            r = subprocess.run(
                ["docker", "images", "-q", image],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if r.returncode == 0 and (r.stdout or "").strip():
                return image
        except (subprocess.TimeoutExpired, FileNotFoundError):
            continue
    return None


def _docker_disponivel() -> bool:
    """Verifica se o Docker está disponível e pelo menos uma imagem pdf2htmlEX existe."""
    return _imagem_docker_disponivel() is not None


def extrair_texto_busca(html: str) -> str:
    """Extrai texto plano do HTML para índice de busca (remove tags, normaliza espaços)."""
    if not html or not html.strip():
        return ""
    # Remove scripts e estilos
    text = re.sub(r"<script[^>]*>[\s\S]*?</script>", " ", html, flags=re.IGNORECASE)
    text = re.sub(r"<style[^>]*>[\s\S]*?</style>", " ", text, flags=re.IGNORECASE)
    # Remove tags
    text = re.sub(r"<[^>]+>", " ", text)
    # Decode entidades comuns
    text = text.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    text = re.sub(r"\s+", " ", text).strip()
    return text[:1_000_000]  # limite razoável para texto_busca


def pdf2htmlex_disponivel() -> bool:
    """Verifica se pdf2htmlEX está disponível (binário no sistema ou Docker com imagem bwits/pdf2htmlex)."""
    if _find_binary() is not None:
        return True
    return _docker_disponivel()


def _executar_via_docker(
    pdf_path: Path,
    output_html_path: Path,
    timeout: int,
    embed_all: bool,
) -> subprocess.CompletedProcess:
    """Executa pdf2htmlEX dentro do container Docker (volume = pasta data)."""
    image = _imagem_docker_disponivel()
    if not image:
        raise RuntimeError(
            "Docker está instalado mas nenhuma imagem pdf2htmlEX encontrada. "
            "Execute: sudo docker pull pdf2htmlex/pdf2htmlex  ou  sudo docker pull bwits/pdf2htmlex"
        )
    pdf_path = Path(pdf_path).resolve()
    output_html_path = Path(output_html_path).resolve()
    output_html_path.parent.mkdir(parents=True, exist_ok=True)
    # Pasta data = pai da pasta html_conteudo (estrutura .../data/html_conteudo/ e .../data/pdf_arespcj/)
    data_root = output_html_path.parent.parent
    try:
        pdf_rel = pdf_path.relative_to(data_root)
    except ValueError:
        raise RuntimeError(
            f"O PDF {pdf_path} não está dentro da pasta data do projeto. "
            "Use caminhos como data/pdf_arespcj/ e data/html_conteudo/."
        )
    # Dentro do container: /work = data_root
    pdf_em_work = Path("/work") / pdf_rel
    out_dir_em_work = Path("/work") / output_html_path.parent.relative_to(data_root)
    out_name = output_html_path.name

    args = [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{data_root}:/work",
        "-w",
        str(out_dir_em_work),
        image,
        "pdf2htmlEX",
    ]
    if embed_all:
        args.extend(["--embed-css", "1", "--embed-font", "1", "--embed-image", "1", "--embed-javascript", "1"])
    args.extend([str(pdf_em_work), out_name])

    return subprocess.run(
        args,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def pdf_para_html_pdf2htmlex(
    pdf_path: Path,
    output_html_path: Path,
    *,
    timeout: int = 120,
    embed_all: bool = True,
) -> tuple[bool, str]:
    """
    Converte um PDF em HTML usando pdf2htmlEX (binário ou Docker).

    Args:
        pdf_path: Caminho do ficheiro PDF.
        output_html_path: Caminho do HTML de saída (ex.: data/html_conteudo/arespcj_2026_688.html).
        timeout: Tempo máximo de execução em segundos.
        embed_all: Se True, passa opções para embutir fontes/imagens no HTML (um único ficheiro).

    Returns:
        (sucesso, texto_busca): True se a conversão correu bem; texto_busca extraído do HTML.
    """
    if not pdf_path.exists() or not pdf_path.is_file():
        raise FileNotFoundError(str(pdf_path))

    output_html_path = Path(output_html_path).resolve()
    output_html_path.parent.mkdir(parents=True, exist_ok=True)
    out_path = output_html_path
    bin_path = _find_binary()
    usar_docker = bin_path is None
    if usar_docker:
        if not _docker_disponivel():
            raise RuntimeError(
                "pdf2htmlEX não está instalado e o Docker não tem a imagem. "
                "Na VPS (Ubuntu): sudo apt install docker.io && sudo docker pull bwits/pdf2htmlex"
            )
        try:
            result = _executar_via_docker(pdf_path, output_html_path, timeout, embed_all)
        except subprocess.TimeoutExpired:
            raise TimeoutError(f"pdf2htmlEX (Docker) excedeu o tempo limite ({timeout}s) para {pdf_path.name}")
    else:
        cwd = str(out_path.parent)
        out_name = out_path.name
        args = [bin_path]
        if embed_all:
            args.extend(["--embed-css", "1", "--embed-font", "1", "--embed-image", "1", "--embed-javascript", "1"])
        args.extend([str(Path(pdf_path).resolve()), out_name])
        try:
            result = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            raise TimeoutError(f"pdf2htmlEX excedeu o tempo limite ({timeout}s) para {pdf_path.name}")
        except FileNotFoundError:
            raise RuntimeError("pdf2htmlEX não encontrado no PATH.")

    if result.returncode != 0:
        stderr = (result.stderr or "").strip() or "(sem mensagem)"
        raise RuntimeError(f"pdf2htmlEX falhou (código {result.returncode}): {stderr}")

    if not out_path.exists():
        raise RuntimeError(f"pdf2htmlEX não criou o ficheiro de saída: {out_path}")

    html = out_path.read_text(encoding="utf-8", errors="replace")
    texto_busca = extrair_texto_busca(html)
    return True, texto_busca
