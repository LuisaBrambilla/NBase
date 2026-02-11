from datetime import date, timedelta
import subprocess
import sys
from pathlib import Path


LOG_DIR = Path("logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_PATH = LOG_DIR / "dodf_mensal.log"
DONE_PATH = LOG_DIR / "dodf_mensal_done.txt"


def primeiro_dia_mes(d: date) -> date:
    return d.replace(day=1)


def ultimo_dia_mes(d: date) -> date:
    prox_mes = (d.replace(day=28) + timedelta(days=4)).replace(day=1)
    return prox_mes - timedelta(days=1)


def iter_meses(inicio: date, fim: date):
    atual = primeiro_dia_mes(inicio)
    fim_mes = primeiro_dia_mes(fim)
    while atual <= fim_mes:
        yield atual
        ano = atual.year + (1 if atual.month == 12 else 0)
        mes = 1 if atual.month == 12 else atual.month + 1
        atual = date(ano, mes, 1)


def main():
    if len(sys.argv) != 3:
        print("Uso: python coletar_dodf_mensal.py YYYY-MM-DD YYYY-MM-DD")
        sys.exit(1)

    inicio = date.fromisoformat(sys.argv[1])
    fim = date.fromisoformat(sys.argv[2])
    if fim < inicio:
        print("Erro: fim deve ser maior ou igual ao inicio.")
        sys.exit(1)

    done = set()
    if DONE_PATH.exists():
        done = set(line.strip() for line in DONE_PATH.read_text().splitlines() if line.strip())

    for mes_inicio in iter_meses(inicio, fim):
        mes_fim = ultimo_dia_mes(mes_inicio)
        if mes_inicio < inicio:
            mes_inicio = inicio
        if mes_fim > fim:
            mes_fim = fim

        key = f"{mes_inicio.isoformat()}_{mes_fim.isoformat()}"
        if key in done:
            print("Pulando (ja concluido):", key)
            continue

        cmd = [
            sys.executable,
            "coletar_dodf.py",
            "--inicio",
            mes_inicio.isoformat(),
            "--fim",
            mes_fim.isoformat(),
            "--secao",
            "ALL",
        ]
        print("Executando:", " ".join(cmd))
        with LOG_PATH.open("a", encoding="utf-8") as log:
            log.write(f"\n== {key} ==\n")
            log.flush()
            subprocess.run(cmd, check=False, stdout=log, stderr=log)

        DONE_PATH.write_text("\n".join(sorted(done | {key})), encoding="utf-8")
        done.add(key)


if __name__ == "__main__":
    main()
