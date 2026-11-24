
from adaptador import adaptar_fila
from conexion_mongo import ConexionMongo
from conexion_mysql import ConexionMySQL


TABLAS_CLAVE_SIMPLE = {
    "categories":  "CategoryID",
    "customers":   "CustomerID",
    "employees":   "EmployeeID",
    "orders":      "OrderID",
    "products":    "ProductID",
    "shippers":    "ShipperID",
    "suppliers":   "SupplierID",
    "usuarios":    "usuario",   # varchar(15), se usa como _id
}

TABLAS_CLAVE_COMPUESTA = ["order_details"]


def _migrar_tabla_simple(mysql, bd_mongo, tabla, campo_id):

    filas = mysql.ejecutar_consulta(f"SELECT * FROM {tabla}")
    coleccion = bd_mongo[tabla]
    coleccion.drop()

    if not filas:
        print(f"  {tabla:20s} → 0 documentos (tabla vacía)")
        return 0

    documentos = []
    for fila in filas:
        doc = adaptar_fila(fila)
        if campo_id in doc:
            doc["_id"] = doc.pop(campo_id)
        documentos.append(doc)

    coleccion.insert_many(documentos, ordered=False)
    print(f"  {tabla:20s} → {len(documentos):>5} documentos insertados")
    return len(documentos)


def _migrar_tabla_compuesta(mysql, bd_mongo, tabla):

    filas = mysql.ejecutar_consulta(f"SELECT * FROM {tabla}")
    coleccion = bd_mongo[tabla]
    coleccion.drop()

    if not filas:
        print(f"  {tabla:20s} → 0 documentos (tabla vacía)")
        return 0

    documentos = [adaptar_fila(fila) for fila in filas]
    coleccion.insert_many(documentos, ordered=False)
    print(f"  {tabla:20s} → {len(documentos):>5} documentos insertados")
    return len(documentos)


def ejecutar_migracion():

    print("\n=== MIGRACIÓN MySQL → MongoDB ===\n")
    conteos = {}

    with ConexionMySQL() as mysql, ConexionMongo() as mongo:
        bd_mongo = mongo.bd

        for tabla, campo_id in TABLAS_CLAVE_SIMPLE.items():
            conteos[tabla] = _migrar_tabla_simple(mysql, bd_mongo, tabla, campo_id)

        for tabla in TABLAS_CLAVE_COMPUESTA:
            conteos[tabla] = _migrar_tabla_compuesta(mysql, bd_mongo, tabla)

    total = sum(conteos.values())
    print(f"\n  Total migrado: {total} documentos en {len(conteos)} colecciones")
    print("=== Migración completada ===\n")
    return conteos



if __name__ == "__main__":
    ESPERADOS = {
        "categories":    8,
        "customers":    91,
        "employees":     9,
        "order_details": 2155,
        "orders":       830,
        "products":      77,
        "shippers":       3,
        "suppliers":     29,
        "usuarios":       0,
    }

    try:
        conteos = ejecutar_migracion()

        print("=== Verificación de conteos ===")
        todos_ok = True
        for tabla, esperado in ESPERADOS.items():
            obtenido = conteos.get(tabla, -1)
            estado = "✓" if obtenido == esperado else "✗"
            if obtenido != esperado:
                todos_ok = False
            print(f"  {estado} {tabla:20s}  esperado={esperado:>5}  obtenido={obtenido:>5}")

        print()
        if todos_ok:
            print("  Todos los conteos coinciden con MySQL.")
        else:
            print("  Hay diferencias. Revisa los mensajes anteriores.")

    except (ConnectionError, RuntimeError) as error:
        print("ERROR:", error)