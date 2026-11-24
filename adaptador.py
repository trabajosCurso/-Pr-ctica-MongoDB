

import datetime
from decimal import Decimal, InvalidOperation

from bson import Decimal128


def convertir_valor(valor):
    if valor is None:
        return None

    if isinstance(valor, str) and valor.startswith("0000-00-00"):
        return None

    if isinstance(valor, Decimal):
        try:
            return Decimal128(str(valor))
        except InvalidOperation:
            return None

    if isinstance(valor, (bytes, bytearray)):
        return None

    if isinstance(valor, datetime.date) and not isinstance(valor, datetime.datetime):
        return datetime.datetime(valor.year, valor.month, valor.day)

    return valor


def adaptar_fila(fila):
    campos_imagen = {"Photo", "Picture", "Image"}

    resultado = {}
    for clave, valor in fila.items():
        valor_convertido = convertir_valor(valor)
        if valor_convertido is None and clave in campos_imagen:
            continue
        resultado[clave] = valor_convertido
    return resultado


if __name__ == "__main__":
    casos = [
        ("Decimal precio",       Decimal("18.00")),
        ("Decimal flete",        Decimal("32.380")),
        ("bytes imagen",         b"\x89PNG\r\n"),
        ("fecha normal",         datetime.datetime(1996, 7, 4, 0, 0)),
        ("fecha date",           datetime.date(1996, 7, 4)),
        ("fecha cero str",       "0000-00-00 00:00:00"),
        ("None",                 None),
        ("int",                  10248),
        ("str",                  "VINET"),
        ("discontinued -1",      -1),
    ]

    print("=== Prueba convertir_valor ===")
    for nombre, val in casos:
        resultado = convertir_valor(val)
        print(f"  {nombre:30s} → {resultado!r}  ({type(resultado).__name__})")

    print()
    fila_ejemplo = {
        "OrderID":      10248,
        "CustomerID":   "VINET",
        "Freight":      Decimal("32.38"),
        "OrderDate":    datetime.datetime(1996, 7, 4),
        "ShippedDate":  "0000-00-00 00:00:00",
        "Photo":        b"\x89PNG",
        "Discontinued": -1,
    }
    print("=== Prueba adaptar_fila ===")
    adaptada = adaptar_fila(fila_ejemplo)
    for k, v in adaptada.items():
        print(f"  {k:20s} → {v!r}  ({type(v).__name__})")
    print()
    if "Photo" not in adaptada:
        print("  ✓ Campo Photo descartado correctamente")
    if adaptada.get("ShippedDate") is None:
        print("  ✓ Fecha 0000-00-00 convertida a None")
    if isinstance(adaptada.get("Freight"), Decimal128):
        print("  ✓ Decimal convertido a Decimal128")