
from decimal import Decimal

from bson import Decimal128

from adaptador import adaptar_fila
from conexion_mongo import ConexionMongo
from conexion_mysql import ConexionMySQL


SQL_ORDENES = """
SELECT
    o.OrderID,
    o.OrderDate,
    o.RequiredDate,
    o.ShippedDate,
    o.Freight,
    o.ShipName,
    o.ShipAddress,
    o.ShipCity,
    o.ShipRegion,
    o.ShipPostalCode,
    o.ShipCountry,
    c.CustomerID,
    c.CompanyName,
    c.ContactName,
    c.City         AS ClienteCity,
    c.Country      AS ClienteCountry,
    e.EmployeeID,
    e.FirstName,
    e.LastName,
    e.Title
FROM orders o
JOIN customers c ON o.CustomerID = c.CustomerID
JOIN employees e ON o.EmployeeID = e.EmployeeID
ORDER BY o.OrderID
"""

SQL_DETALLES = """
SELECT
    od.OrderID,
    od.ProductID,
    p.ProductName,
    cat.CategoryName,
    od.UnitPrice,
    od.Quantity,
    od.Discount
FROM order_details od
JOIN products      p   ON od.ProductID  = p.ProductID
JOIN categories    cat ON p.CategoryID  = cat.CategoryID
ORDER BY od.OrderID, od.ProductID
"""



def _calcular_subtotal(unit_price, quantity, discount):

    precio = unit_price if isinstance(unit_price, Decimal) else Decimal(str(unit_price))
    desc   = Decimal(str(discount)) if not isinstance(discount, Decimal) else discount
    subtotal = precio * Decimal(str(quantity)) * (Decimal("1") - desc)
    return Decimal128(str(subtotal.quantize(Decimal("0.0001"))))


def _construir_detalles_por_orden(filas_detalles):

    detalles = {}
    for fila in filas_detalles:
        oid = fila["OrderID"]
        subtotal = _calcular_subtotal(
            fila["UnitPrice"], fila["Quantity"], fila["Discount"]
        )
        linea = {
            "ProductID":    fila["ProductID"],
            "ProductName":  fila["ProductName"],
            "CategoryName": fila["CategoryName"],
            "UnitPrice":    Decimal128(str(
                fila["UnitPrice"] if isinstance(fila["UnitPrice"], Decimal)
                else Decimal(str(fila["UnitPrice"]))
            )),
            "Quantity":     fila["Quantity"],
            "Discount":     float(fila["Discount"]),
            "Subtotal":     subtotal,
        }
        detalles.setdefault(oid, []).append(linea)
    return detalles


def _construir_documento(fila_orden, detalles_orden):
    doc = adaptar_fila({
        "OrderDate":     fila_orden["OrderDate"],
        "RequiredDate":  fila_orden["RequiredDate"],
        "ShippedDate":   fila_orden["ShippedDate"],
        "Freight":       fila_orden["Freight"],
        "ShipName":      fila_orden["ShipName"],
        "ShipAddress":   fila_orden["ShipAddress"],
        "ShipCity":      fila_orden["ShipCity"],
        "ShipRegion":    fila_orden["ShipRegion"],
        "ShipPostalCode":fila_orden["ShipPostalCode"],
        "ShipCountry":   fila_orden["ShipCountry"],
    })
    doc["_id"] = fila_orden["OrderID"]

    doc["cliente"] = {
        "CustomerID":  fila_orden["CustomerID"],
        "CompanyName": fila_orden["CompanyName"],
        "ContactName": fila_orden["ContactName"],
        "City":        fila_orden["ClienteCity"],
        "Country":     fila_orden["ClienteCountry"],
    }

    doc["empleado"] = {
        "EmployeeID": fila_orden["EmployeeID"],
        "FirstName":  fila_orden["FirstName"],
        "LastName":   fila_orden["LastName"],
        "Title":      fila_orden["Title"],
    }

    doc["detalles"] = detalles_orden

    return doc


def construir_ordertotal():

    print("\n=== CONSTRUYENDO Ordertotal ===\n")

    with ConexionMySQL() as mysql, ConexionMongo() as mongo:
        print("  Leyendo órdenes desde MySQL...")
        filas_ordenes  = mysql.ejecutar_consulta(SQL_ORDENES)
        print(f"  {len(filas_ordenes)} órdenes leídas")

        print("  Leyendo detalles desde MySQL...")
        filas_detalles = mysql.ejecutar_consulta(SQL_DETALLES)
        print(f"  {len(filas_detalles)} líneas de detalle leídas")

        print("  Agrupando detalles por orden...")
        detalles_por_orden = _construir_detalles_por_orden(filas_detalles)

        print("  Construyendo documentos...")
        documentos = []
        for fila in filas_ordenes:
            oid = fila["OrderID"]
            detalles = detalles_por_orden.get(oid, [])
            documentos.append(_construir_documento(fila, detalles))

        coleccion = mongo.bd["Ordertotal"]
        coleccion.drop()
        coleccion.insert_many(documentos, ordered=False)

        total = len(documentos)
        print(f"\n  Ordertotal → {total} documentos insertados")
        print("=== Ordertotal completado ===\n")
        return total



if __name__ == "__main__":
    try:
        total = construir_ordertotal()

        with ConexionMongo() as mongo:
            col = mongo.bd["Ordertotal"]

            conteo_mongo = col.count_documents({})
            estado = "✓" if conteo_mongo == total else "✗"
            print(f"  {estado} Documentos en Ordertotal: {conteo_mongo} (esperado {total})")

            muestra = col.find_one({"_id": 10248})
            if muestra:
                print("\n  Muestra OrderID 10248:")
                print(f"    _id        : {muestra['_id']}")
                print(f"    OrderDate  : {muestra.get('OrderDate')}")
                print(f"    ShippedDate: {muestra.get('ShippedDate')}")
                print(f"    Freight    : {muestra.get('Freight')}")
                print(f"    cliente    : {muestra['cliente']['CompanyName']} "
                      f"({muestra['cliente']['CustomerID']})")
                print(f"    empleado   : {muestra['empleado']['FirstName']} "
                      f"{muestra['empleado']['LastName']}")
                print(f"    detalles   : {len(muestra['detalles'])} líneas")
                if muestra["detalles"]:
                    d = muestra["detalles"][0]
                    print(f"      primera línea → {d['ProductName']:30s} "
                          f"x{d['Quantity']}  subtotal={d['Subtotal']}")

            sin_fecha = col.find_one({"ShippedDate": None, "_id": {"$gte": 1}})
            if sin_fecha:
                print(f"\n  ✓ Pedido con ShippedDate=null encontrado: "
                      f"OrderID {sin_fecha['_id']}")
            else:
                print("\n  (ningún pedido con ShippedDate=null encontrado)")

    except (ConnectionError, RuntimeError) as error:
        print("ERROR:", error)