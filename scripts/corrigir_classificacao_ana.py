"""
Atualiza em massa status (vigente/nao_vigente/vigente_alterado) e assunto das normas
ANA (origem govbr) conforme listas fornecidas. Marca as normas como já aprovadas
(verificacao_status='aprovado') para aparecerem em Verificações aprovadas.

Uso (na raiz do projeto, venv ativo):
  python scripts/corrigir_classificacao_ana.py
  python scripts/corrigir_classificacao_ana.py --dry-run   # só mostra o que faria
  python scripts/corrigir_classificacao_ana.py --status-only
  python scripts/corrigir_classificacao_ana.py --assunto-only
"""

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from db.db import get_connection

ORIGEM = "govbr"

# (ano) -> { "vigente": [números], "nao_vigente": [...], "vigente_alterado": [...] }
STATUS_POR_ANO = {
    2001: {"vigente": [56], "nao_vigente": [130, 7, 6], "vigente_alterado": []},
    2002: {"vigente": [194, 177], "nao_vigente": [26, 145, 70, 71, 210, 135, 82, 362, 27, 44, 193], "vigente_alterado": []},
    2003: {"vigente": [], "nao_vigente": [330, 193, 434, 282, 408, 211, 258, 269, 161], "vigente_alterado": [131, 317]},
    2004: {"vigente": [223, 399], "nao_vigente": [139, 215, 210, 211, 216, 213, 209, 214, 212, 530, 244, 424, 653, 98, 529, 465, 428, 687, 327, 250, 31, 707, 425, 245, 551], "vigente_alterado": [429]},
    2005: {"vigente": [163], "nao_vigente": [219, 417, 418, 497, 499, 61, 132, 512, 464, 435], "vigente_alterado": []},
    2006: {"vigente": [451], "nao_vigente": [122, 469, 467, 127, 298, 547, 121, 303, 597, 258], "vigente_alterado": []},
    2007: {"vigente": [97], "nao_vigente": [117, 224, 80, 354, 602, 242, 96, 308, 479], "vigente_alterado": []},
    2008: {"vigente": [], "nao_vigente": [142, 138, 52, 51, 804, 650, 803, 306, 796], "vigente_alterado": []},
    2009: {"vigente": [714, 276], "nao_vigente": [655, 779, 160, 371, 370, 782], "vigente_alterado": []},
    2010: {"vigente": [77, 614, 716], "nao_vigente": [613, 127, 267, 3, 466, 562, 662, 418], "vigente_alterado": []},
    2011: {"vigente": [872, 33], "nao_vigente": [71, 873, 691, 376, 553, 742, 833, 724, 552], "vigente_alterado": []},
    2012: {"vigente": [463, 465, 25], "nao_vigente": [145, 607, 147, 326, 91], "vigente_alterado": []},
    2013: {"vigente": [379, 512, 353, 1286, 1343, 1485, 1225], "nao_vigente": [1403, 644, 1289, 1041, 1406, 1589, 442, 1175, 1346], "vigente_alterado": [903, 436]},
    2014: {"vigente": [1941, 683, 1624, 1399, 99, 1041], "nao_vigente": [672, 1524, 1040, 1047, 2018, 100, 1631, 102, 333, 680, 1046, 1258, 1514, 1604, 1778, 2050, 910, 1038, 1072, 2048, 1779, 2051, 336, 699, 335, 700, 96, 898, 1309, 1516, 1603, 2019, 641], "vigente_alterado": []},
    2015: {"vigente": [961, 1382, 147, 51, 50, 1305, 1310, 1201], "nao_vigente": [768, 1273, 774, 1072, 962, 601, 1203, 603, 632, 85, 132, 499, 1493, 560, 602, 1307, 206, 1208, 1492, 852, 713, 714, 205, 1204, 86, 633, 960, 1202, 316, 145, 1494, 640, 639, 148], "vigente_alterado": []},
    2016: {"vigente": [1058, 643, 1595, 5], "nao_vigente": [144, 436, 1047, 1162, 1254, 126, 127, 128, 129, 130, 131, 66, 1161, 1283, 287, 642, 934, 560, 65, 1188, 288, 561, 407, 1163, 1397, 132, 1396, 1594], "vigente_alterado": [1190]},
    2017: {"vigente": [1935, 1506, 925, 2081, 1564, 1470, 2079, 336, 1931, 1936], "nao_vigente": [1769, 347, 478, 1291, 1939, 2333, 2334, 224, 742, 1943, 1098, 335, 743, 1469, 1570, 588, 584, 1940, 1937, 1938, 2219, 1, 1941, 1932, 1043, 2082, 567, 1292, 1290, 1277], "vigente_alterado": [590, 969, 589, 585, 587, 236]},
    2018: {"vigente": [102, 67, 49, 69, 75, 54, 70, 61, 55, 63, 100, 98, 11, 96, 66, 1, 65], "nao_vigente": [73, 72, 33, 45, 17, 31, 93, 8, 30, 50, 9, 51, 90, 99, 87, 97, 20, 91, 4, 12, 92], "vigente_alterado": [101, 76, 52, 85]},
    2019: {"vigente": [61, 62, 6, 58, 60, 59, 64, 73, 65, 56, 122, 66], "nao_vigente": [74, 19, 57, 43, 101, 15, 99, 97, 78, 11], "vigente_alterado": [125, 124]},
    2020: {"vigente": [27, 58, 11, 42, 55, 51, 43, 21, 39, 17, 49, 50, 40, 18, 30, 59, 28, 31, 34, 46], "nao_vigente": [25, 19, 56, 4, 22, 20, 57, 24, 23, 2, 52], "vigente_alterado": [29, 53]},
    2021: {"vigente": [78, 144, 67, 84, 81, 77, 98, 74, 82, 65, 76, 66, 109, 93, 92, 63, 80, 90, 101, 83, 96, 70, 100, 94, 112], "nao_vigente": [106, 102, 91, 72, 111, 110, 108, 113], "vigente_alterado": [79]},
    2022: {"vigente": [121, 122, 117, 134, 142, 132, 140, 141, 126, 118, 119, 116, 125, 127, 120], "nao_vigente": [139], "vigente_alterado": [135]},
    2023: {"vigente": [160, 165, 148, 161, 164, 143, 146, 170, 171, 145, 169, 153], "nao_vigente": [156, 174, 154, 172], "vigente_alterado": [159, 168, 173]},
    2024: {"vigente": [197, 199, 228, 230, 177, 178, 187, 192, 211, 180, 190, 223, 195, 214, 212, 202, 203, 225, 188, 210, 196, 189, 232, 193, 194, 186, 234, 221, 209, 231, 207, 219, 175, 206, 179, 181, 204], "nao_vigente": [235, 205, 227, 213, 226, 233], "vigente_alterado": [183, 236]},
    2025: {"vigente": [267, 273, 266, 252, 271, 276, 245, 275, 277, 264, 237, 260, 248, 265, 274, 256, 278, 258, 238], "nao_vigente": [], "vigente_alterado": [246]},
}


def parse_numero_ano(s: str) -> list[tuple[int, int]]:
    """Extrai pares (ano, numero) de texto como '961 (2015), 399 (2004)'."""
    out = []
    # padrão: numero (ano) ou numero(ano)
    for m in re.finditer(r"(\d+)\s*\(\s*(\d{4})\s*\)", s):
        numero, ano = int(m.group(1)), int(m.group(2))
        out.append((ano, numero))
    return out


# Assunto -> lista de (ano, numero). Texto colado da mensagem do usuário.
ASSUNTOS_RAW = """
1) Regulação de Usos de Recursos Hídricos: 961 (2015), 399 (2004), 235 (2024), 156 (2023), 205 (2024), 273 (2025), 101 (2018), 102 (2018), 61 (2019), 1935 (2017), 1058 (2016), 962 (2015), 73 (2018), 72 (2018), 1403 (2013), 78 (2021), 33 (2018), 45 (2018), 25 (2020), 463 (2012), 147 (2012), 683 (2014), 56 (2020), 42 (2020), 436 (2016), 1047 (2016), 1162 (2016), 326 (2012), 223 (2024), 195 (2024), 77 (2021), 214 (2024), 212 (2024), 264 (2025), 202 (2024), 203 (2024), 1254 (2016), 237 (2025), 353 (2013), 193 (2003), 1041 (2013), 213 (2024), 210 (2024), 1047 (2014), 429 (2004), 52 (2008), 51 (2008), 804 (2008), 77 (2010), 219 (2005), 1939 (2017), 82 (2021), 260 (2025), 146 (2023), 779 (2009), 196 (2024), 189 (2024), 170 (2023), 910 (2014), 122 (2006), 21 (2020), 336 (2014), 699 (2014), 66 (2021), 69 (2018), 1098 (2017), 109 (2021), 58 (2019), 75 (2018), 60 (2019), 59 (2019), 1564 (2017), 1470 (2017), 64 (2019), 73 (2019), 49 (2020), 65 (2019), 90 (2021), 50 (2020), 40 (2020), 76 (2018), 101 (2021), 54 (2018), 126 (2022), 56 (2019), 118 (2022), 70 (2018), 52 (2018), 61 (2018), 119 (2022), 590 (2017), 588 (2017), 969 (2017), 55 (2018), 589 (2017), 585 (2017), 584 (2017), 587 (2017), 83 (2021), 1940 (2017), 1175 (2013), 467 (2006), 872 (2011), 127 (2010), 96 (2014), 1937 (2017), 407 (2016), 633 (2015), 30 (2020), 127 (2006), 687 (2004), 236 (2024), 497 (2005), 327 (2004), 210 (2002), 499 (2005), 250 (2004), 31 (2004), 553 (2011), 267 (2010), 43 (2019), 154 (2023), 286 (2026), 135 (2002), 707 (2004), 61 (2005), 1938 (2017), 131 (2003), 1286 (2013), 1163 (2016), 87 (2018), 833 (2011), 466 (2010), 51 (2015), 50 (2015), 960 (2015), 1397 (2016), 100 (2021), 425 (2004), 782 (2009), 1305 (2015), 479 (2007), 25 (2012), 1343 (2013), 221 (2024), 274 (2025), 256 (2025), 44 (2002), 2219 (2017), 562 (2010), 547 (2006), 1 (2017), 1941 (2017), 1399 (2014), 436 (2013), 269 (2003), 2079 (2017), 11 (2018), 1202 (2015), 1932 (2017), 316 (2015), 1043 (2017), 2082 (2017), 66 (2019), 418 (2010), 1292 (2017), 12 (2018), 1290 (2017), 219 (2024), 175 (2024), 206 (2024), 1277 (2017), 317 (2003), 1396 (2016), 1310 (2015), 303 (2006), 597 (2006), 276 (2009), 193 (2002), 78 (2019), 161 (2003), 46 (2020), 11 (2019), 1494 (2015), 640 (2015), 5 (2016), 551 (2004), 1225 (2013), 96 (2018), 204 (2024), 99 (2014), 1201 (2015), 66 (2018), 1 (2018), 1936 (2017), 65 (2018), 1041 (2014), 639 (2015), 148 (2015).

2) Regras para Operação de Reservatórios: 768 (2015), 139 (2004), 1769 (2017), 347 (2017), 215 (2004), 210 (2004), 211 (2004), 216 (2004), 213 (2004), 209 (2004), 214 (2004), 212 (2004), 84 (2021), 55 (2020), 117 (2022), 81 (2021), 51 (2020), 478 (2017), 1291 (2017), 31 (2018), 164 (2023), 100 (2014), 2334 (2017), 1631 (2014), 65 (2021), 93 (2018), 4 (2020), 22 (2020), 85 (2015), 132 (2015), 499 (2015), 102 (2014), 333 (2014), 680 (2014), 1046 (2014), 1258 (2014), 1406 (2014), 1258 (2014), 1406 (2013), 1514 (2014), 1589 (2013), 1604 (2014), 1778 (2014), 2050 (2014), 8 (2018), 1038 (2014), 1072 (2014), 2048 (2014), 1493 (2015), 98 (2004), 560 (2015), 30 (2018), 66 (2016), 224 (2017), 602 (2007), 602 (2015), 742 (2017), 1161 (2016), 1283 (2016), 1307 (2015), 1943 (2017), 206 (2015), 287 (2016), 434 (2003), 442 (2013), 642 (2016), 803 (2008), 1208 (2015), 1492 (2015), 852 (2015), 934 (2016), 50 (2018), 72 (2021), 9 (2018), 76 (2021), 51 (2018), 90 (2018), 19 (2019), 713 (2015), 282 (2003), 418 (2005), 160 (2009), 371 (2009), 560 (2016), 714 (2015), 65 (2016), 1188 (2016), 205 (2015), 288 (2016), 1204 (2015), 86 (2015), 1779 (2014), 2051 (2014), 561 (2016), 408 (2003), 1382 (2015), 370 (2009), 147 (2015), 529 (2004), 99 (2018), 57 (2019), 49 (2018), 465 (2004), 376 (2011), 614 (2010), 428 (2004), 925 (2017), 335 (2014), 335 (2017), 743 (2017), 1469 (2017), 1570 (2017), 2081 (2017), 111 (2021), 142 (2022), 211 (2003), 96 (2007), 63 (2021), 80 (2021), 132 (2022), 193 (2024), 194 (2024), 110 (2021), 140 (2022), 141 (2022), 108 (2021), 700 (2014), 898 (2014), 1309 (2014), 1516 (2014), 1603 (2014), 298 (2006), 70 (2021), 567 (2017), 4 (2018), 31 (2020), 336 (2017), 52 (2020), 112 (2021), 97 (2019), 1594 (2016), 92 (2018), 258 (2006), 435 (2005), 145 (2015), 1931 (2017).

3) Monitoramento Hidrológico: 1273 (2015), 1072 (2015), 643 (2016), 199 (2024), 903 (2013), 1040 (2014), 159 (2023), 225 (2024), 3 (2010), 1624 (2014), 724 (2011), 207 (2024), 127 (2022).

4) Planejamento e Informação de Recursos Hídricos: 93 (2021), 92 (2021), 23 (2020), 2 (2020), 99 (2019).

5) Implementação da Política Nacional de Recursos Hídricos: 223 (2004), 774 (2015), 26 (2002), 160 (2023), 266 (2025), 62 (2019), 117 (2007), 224 (2007), 17 (2018), 180 (2024), 655 (2009), 71 (2011), 145 (2012), 672 (2014), 873 (2011), 1595 (2016), 451 (2006), 379 (2013), 512 (2013), 530 (2004), 80 (2007), 644 (2013), 601 (2015), 1190 (2016), 244 (2004), 424 (2004), 354 (2007), 691 (2011), 607 (2012), 1289 (2013), 1524 (2014), 1203 (2015), 138 (2008), 330 (2003), 653 (2004), 144 (2016), 613 (2010), 70 (2002), 56 (2001), 1506 (2017), 98 (2021), 71 (2002), 2018 (2014), 74 (2021), 143 (2023), 650 (2008), 18 (2020), 29 (2020), 171 (2023), 20 (2020), 234 (2024), 124 (2019), 308 (2007), 362 (2002), 98 (2018), 132 (2005), 258 (2003), 97 (2007), 97 (2018), 94 (2021), 163 (2005), 512 (2005), 101 (2019), 20 (2018), 91 (2018), 27 (2002), 7 (2001), 117 (2002), 278 (2025), 57 (2020), 113 (2021), 139 (2022), 172 (2023), 233 (2024), 245 (2004), 121 (2006), 306 (2008), 464 (2005), 122 (2019), 28 (2020), 2019 (2014), 15 (2019), 125 (2022), 1485 (2013), 552 (2011), 153 (2023), 6 (2001), 181 (2024), 135 (2022), 796 (2008), 53 (2020), 120 (2022).

6) Fiscalização: 142 (2008), 27 (2020), 126 (2016), 127 (2016), 128 (2016), 129 (2016), 130 (2016), 131 (2016), 91 (2021), 603 (2015), 188 (2024), 632 (2015), 232 (2014), 82 (2002), 96 (2021), 24 (2020), 662 (2010), 231 (2024), 33 (2011), 716 (2010).

7) Regulação de Serviços: 74 (2019), 267 (2025), 197 (2024), 58 (2020), 252 (2025), 165 (2023), 145 (2002), 67 (2018), 11 (2020), 67 (2021), 148 (2023), 190 (2024), 6 (2019), 122 (2022), 246 (2025), 714 (2009), 2333 (2017), 39 (2020), 17 (2020), 168 (2023), 125 (2019), 63 (2018), 100 (2018), 59 (2020), 145 (2023), 173 (2023), 226 (2024), 116 (2022), 85 (2018), 248 (2025), 194 (2002), 641 (2014).

8) Segurança de Barragens: 121 (2022), 91 (2012), 236 (2017), 742 (2011), 132 (2016), 265 (2025).

9) Saneamento Básico: 114 (2021), 271 (2025), 276 (2025), 183 (2024), 106 (2021), 79 (2021), 228 (2024), 230 (2024), 245 (2025), 275 (2025), 177 (2024), 178 (2024), 187 (2024), 192 (2024), 211 (2024), 161 (2023), 134 (2022), 169 (2023), 258 (2025), 209 (2024), 179 (2024), 238 (2025).
"""


def build_assuntos_map() -> dict[str, list[tuple[int, int]]]:
    assuntos = {}
    for line in ASSUNTOS_RAW.strip().split("\n"):
        line = line.strip()
        if not line or not line[0].isdigit():
            continue
        # "1) Nome do assunto: 123 (2020), ..."
        idx = line.find(")")
        if idx == -1:
            continue
        rest = line[idx + 1 :].strip()
        if ": " not in rest:
            continue
        nome, nums = rest.split(": ", 1)
        nome = nome.strip()
        assuntos[nome] = parse_numero_ano(nums)
    return assuntos


ASSUNTOS_MAP = build_assuntos_map()


def main() -> int:
    ap = argparse.ArgumentParser(description="Corrigir status e assunto das normas ANA (govbr)")
    ap.add_argument("--dry-run", action="store_true", help="Não gravar; só mostrar o que faria")
    ap.add_argument("--status-only", action="store_true", help="Só atualizar status")
    ap.add_argument("--assunto-only", action="store_true", help="Só atualizar assunto")
    args = ap.parse_args()
    dry = args.dry_run

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Obter um admin_id para marcar verificacao_admin_id (normas aprovadas em lote)
            cur.execute("SELECT id FROM admins WHERE ativo = true LIMIT 1")
            row = cur.fetchone()
            admin_id = str(row["id"]) if row else None
            if not admin_id:
                print("Aviso: Nenhum admin ativo. verificacao_admin_id ficará NULL (normas podem não aparecer em Verificações aprovadas).")

            updated_status = 0
            if not args.assunto_only:
                for ano, grupos in STATUS_POR_ANO.items():
                    for status_val, numeros in grupos.items():
                        if not numeros:
                            continue
                        for numero in numeros:
                            if dry:
                                print(f"[DRY-RUN] UPDATE norma SET status={status_val!r}, verificacao_status='aprovado' WHERE ano={ano} AND numero={numero} AND origem={ORIGEM!r}")
                            else:
                                cur.execute(
                                    """
                                    UPDATE norma
                                    SET status = %s, verificacao_status = 'aprovado', verificacao_em = now(),
                                        verificacao_admin_id = %s
                                    WHERE ano = %s AND numero = %s AND origem = %s
                                    """,
                                    (status_val, admin_id, ano, numero, ORIGEM),
                                )
                                updated_status += cur.rowcount
                print(f"Status atualizados: {updated_status}")

                # Marcar como aprovadas todas as demais normas ANA (govbr) ainda pendentes,
                # para que as 548 apareçam em Verificações aprovadas (as 8 que não estavam nas listas).
                if not dry and admin_id:
                    cur.execute(
                        """
                        UPDATE norma
                        SET verificacao_status = 'aprovado', verificacao_em = now(), verificacao_admin_id = %s
                        WHERE origem = %s AND (verificacao_status IS NULL OR verificacao_status = 'pendente')
                        """,
                        (admin_id, ORIGEM),
                    )
                    restantes = cur.rowcount
                    if restantes:
                        print(f"Normas ANA (govbr) restantes marcadas como aprovadas: {restantes}")

            updated_assunto = 0
            if not args.status_only:
                for assunto_nome, pares in ASSUNTOS_MAP.items():
                    for ano, numero in pares:
                        if dry:
                            print(f"[DRY-RUN] UPDATE norma SET assunto={assunto_nome[:50]!r} WHERE ano={ano} AND numero={numero} AND origem={ORIGEM!r}")
                        else:
                            cur.execute(
                                """
                                UPDATE norma SET assunto = %s
                                WHERE ano = %s AND numero = %s AND origem = %s
                                """,
                                (assunto_nome, ano, numero, ORIGEM),
                            )
                            updated_assunto += cur.rowcount
                print(f"Assuntos atualizados: {updated_assunto}")

        if not dry:
            conn.commit()
        else:
            print("[DRY-RUN] Nada foi gravado.")
    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
