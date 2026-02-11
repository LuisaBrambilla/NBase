import sys
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from db.db import get_connection

STATUS_VIGENTE = "vigente"
STATUS_ALTERADO = "vigente_alterado"
STATUS_REVOGADO = "nao_vigente"

STATUS_POR_ANO: Dict[int, Dict[str, List[int]]] = {
    2001: {
        STATUS_VIGENTE: [56],
        STATUS_REVOGADO: [130, 7, 6],
    },
    2002: {
        STATUS_VIGENTE: [194, 177],
        STATUS_REVOGADO: [26, 145, 70, 71, 210, 135, 82, 362, 27, 44, 193],
    },
    2003: {
        STATUS_ALTERADO: [131, 317],
        STATUS_REVOGADO: [330, 193, 434, 282, 408, 211, 258, 269, 161],
    },
    2004: {
        STATUS_VIGENTE: [223, 399],
        STATUS_ALTERADO: [429],
        STATUS_REVOGADO: [
            139,
            215,
            210,
            211,
            216,
            213,
            209,
            214,
            212,
            530,
            244,
            424,
            653,
            98,
            529,
            465,
            428,
            687,
            327,
            250,
            31,
            707,
            425,
            245,
            551,
        ],
    },
    2005: {
        STATUS_VIGENTE: [163],
        STATUS_REVOGADO: [219, 417, 418, 497, 499, 61, 132, 512, 464, 435],
    },
    2006: {
        STATUS_VIGENTE: [451],
        STATUS_REVOGADO: [122, 469, 467, 127, 298, 547, 121, 303, 597, 258],
    },
    2007: {
        STATUS_VIGENTE: [97],
        STATUS_REVOGADO: [117, 224, 80, 354, 602, 242, 96, 308, 479],
    },
    2008: {
        STATUS_REVOGADO: [142, 138, 52, 51, 804, 650, 803, 306, 796],
    },
    2009: {
        STATUS_VIGENTE: [714, 276],
        STATUS_REVOGADO: [655, 779, 160, 371, 370, 782],
    },
    2010: {
        STATUS_VIGENTE: [77, 614, 716],
        STATUS_REVOGADO: [613, 127, 267, 3, 466, 562, 662, 418],
    },
    2011: {
        STATUS_VIGENTE: [872, 33],
        STATUS_REVOGADO: [71, 873, 691, 376, 553, 742, 833, 724, 552],
    },
    2012: {
        STATUS_VIGENTE: [463, 465, 25],
        STATUS_REVOGADO: [145, 607, 147, 326, 91],
    },
    2013: {
        STATUS_VIGENTE: [379, 512, 353, 1286, 1343, 1485, 1225],
        STATUS_ALTERADO: [903, 436],
        STATUS_REVOGADO: [1403, 644, 1289, 1041, 1406, 1589, 442, 1175, 1346],
    },
    2014: {
        STATUS_VIGENTE: [1941, 683, 1624, 1399, 99, 1041],
        STATUS_REVOGADO: [
            672,
            1524,
            1040,
            1047,
            2018,
            100,
            1631,
            102,
            333,
            680,
            1046,
            1258,
            1514,
            1604,
            1778,
            2050,
            910,
            1038,
            1072,
            2048,
            1779,
            2051,
            336,
            699,
            335,
            700,
            96,
            898,
            1309,
            1516,
            1603,
            2019,
            641,
        ],
    },
    2015: {
        STATUS_VIGENTE: [961, 1382, 147, 51, 50, 1305, 1310, 1201],
        STATUS_REVOGADO: [
            768,
            1273,
            774,
            1072,
            962,
            601,
            1203,
            603,
            632,
            85,
            132,
            499,
            1493,
            560,
            602,
            1307,
            206,
            1208,
            1492,
            852,
            713,
            714,
            205,
            1204,
            86,
            633,
            960,
            1202,
            316,
            145,
            1494,
            640,
            639,
            148,
        ],
    },
    2016: {
        STATUS_VIGENTE: [1058, 643, 1595, 5],
        STATUS_ALTERADO: [1190],
        STATUS_REVOGADO: [
            144,
            436,
            1047,
            1162,
            1254,
            126,
            127,
            128,
            129,
            130,
            131,
            66,
            1161,
            1283,
            287,
            642,
            934,
            560,
            65,
            1188,
            288,
            561,
            407,
            1163,
            1397,
            132,
            1396,
            1594,
        ],
    },
    2017: {
        STATUS_VIGENTE: [1935, 1506, 925, 2081, 1564, 1470, 2079, 336, 1931, 1936],
        STATUS_ALTERADO: [590, 969, 589, 585, 587, 236],
        STATUS_REVOGADO: [
            1769,
            347,
            478,
            1291,
            1939,
            2333,
            2334,
            224,
            742,
            1943,
            1098,
            335,
            743,
            1469,
            1570,
            588,
            584,
            1940,
            1937,
            1938,
            2219,
            1,
            1941,
            1932,
            1043,
            2082,
            567,
            1292,
            1290,
            1277,
        ],
    },
    2018: {
        STATUS_VIGENTE: [102, 67, 49, 69, 75, 54, 70, 61, 55, 63, 100, 98, 11, 96, 66, 1, 65],
        STATUS_ALTERADO: [101, 76, 52, 85],
        STATUS_REVOGADO: [
            73,
            72,
            33,
            45,
            17,
            31,
            93,
            8,
            30,
            50,
            9,
            51,
            90,
            99,
            87,
            97,
            20,
            91,
            4,
            12,
            92,
        ],
    },
    2019: {
        STATUS_VIGENTE: [61, 62, 6, 58, 60, 59, 64, 73, 65, 56, 122, 66],
        STATUS_ALTERADO: [125, 124],
        STATUS_REVOGADO: [74, 19, 57, 43, 101, 15, 99, 97, 78, 11],
    },
    2020: {
        STATUS_VIGENTE: [
            27,
            58,
            11,
            42,
            55,
            51,
            43,
            21,
            39,
            17,
            49,
            50,
            40,
            18,
            30,
            59,
            28,
            31,
            34,
            46,
        ],
        STATUS_ALTERADO: [29, 53],
        STATUS_REVOGADO: [25, 19, 56, 4, 22, 20, 57, 24, 23, 2, 52],
    },
    2021: {
        STATUS_VIGENTE: [
            78,
            144,
            67,
            84,
            81,
            77,
            98,
            74,
            82,
            65,
            76,
            66,
            109,
            93,
            92,
            63,
            80,
            90,
            101,
            83,
            96,
            70,
            100,
            94,
            112,
        ],
        STATUS_ALTERADO: [79],
        STATUS_REVOGADO: [106, 102, 91, 72, 111, 110, 108, 113],
    },
    2022: {
        STATUS_VIGENTE: [121, 122, 117, 134, 142, 132, 140, 141, 126, 118, 119, 116, 125, 127, 120],
        STATUS_ALTERADO: [135],
        STATUS_REVOGADO: [139],
    },
    2023: {
        STATUS_VIGENTE: [160, 165, 148, 161, 164, 143, 146, 170, 171, 145, 169, 153],
        STATUS_ALTERADO: [159, 168, 173],
        STATUS_REVOGADO: [156, 174, 154, 172],
    },
    2024: {
        STATUS_VIGENTE: [
            197,
            199,
            228,
            230,
            177,
            178,
            187,
            192,
            211,
            180,
            190,
            223,
            195,
            214,
            212,
            202,
            203,
            225,
            188,
            210,
            196,
            189,
            232,
            193,
            194,
            186,
            234,
            221,
            209,
            231,
            207,
            219,
            175,
            206,
            179,
            181,
            204,
        ],
        STATUS_ALTERADO: [183, 236],
        STATUS_REVOGADO: [235, 205, 227, 213, 226, 233],
    },
    2025: {
        STATUS_VIGENTE: [267, 273, 266, 252, 271, 276, 245, 275, 277, 264, 237, 260, 248, 265, 274, 256, 278, 258, 238],
        STATUS_ALTERADO: [246],
    },
}


def atualizar_status(conn) -> None:
    total_alterados = 0
    faltando: List[str] = []
    with conn.cursor() as cur:
        for ano, grupos in STATUS_POR_ANO.items():
            for status, numeros in grupos.items():
                if not numeros:
                    continue
                cur.execute(
                    """
                    UPDATE norma
                    SET status = %s
                    WHERE ano = %s
                      AND numero = ANY(%s)
                      AND origem = 'govbr'
                    """,
                    (status, ano, numeros),
                )
                atualizados = cur.rowcount
                total_alterados += atualizados
                if atualizados < len(numeros):
                    # Descobre quais numeros nao foram encontrados
                    cur.execute(
                        """
                        SELECT numero
                        FROM norma
                        WHERE ano = %s
                          AND numero = ANY(%s)
                          AND origem = 'govbr'
                        """,
                        (ano, numeros),
                    )
                    # Com RealDictCursor, cada linha vem como dict (ex.: {"numero": 123}).
                    # Mantemos compatibilidade caso venha tupla em outros ambientes.
                    encontrados = {
                        row["numero"] if isinstance(row, dict) else row[0]
                        for row in cur.fetchall()
                    }
                    for num in numeros:
                        if num not in encontrados:
                            faltando.append(f"{ano}-{num}")
    conn.commit()
    print(f"Total atualizados: {total_alterados}")
    if faltando:
        print("Não encontrados:")
        print(", ".join(faltando))


def main() -> int:
    try:
        conn = get_connection()
    except Exception as exc:
        print("Erro ao conectar no banco:", exc)
        return 1
    try:
        atualizar_status(conn)
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
