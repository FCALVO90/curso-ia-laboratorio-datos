// ============================================================
// CLASE 04 - TALLER DE QUERIES MONGODB
// BASE DE DATOS: curso_ia
// COLECCION: online_retail_ii
// ============================================================


// ============================================================
// EJERCICIO 1
// Mostrar los primeros 10 documentos.
// Equivalencia SQL:
// SELECT * FROM online_retail_ii LIMIT 10;
// ============================================================

print("\n========== EJERCICIO 1 ==========");

db.online_retail_ii
    .find()
    .limit(10)
    .forEach(printjson);


// ============================================================
// EJERCICIO 2
// Contar el numero total de documentos.
// Equivalencia SQL: COUNT(*)
// ============================================================

print("\n========== EJERCICIO 2 ==========");

printjson({
    total_registros: db.online_retail_ii.countDocuments()
});


// ============================================================
// EJERCICIO 3
// Obtener todos los paises diferentes.
// Ordenarlos alfabeticamente.
// Equivalencia SQL: SELECT DISTINCT
// ============================================================

print("\n========== EJERCICIO 3 ==========");

printjson(
    db.online_retail_ii.distinct("country").sort()
);


// ============================================================
// EJERCICIO 4
// Mostrar las primeras 10 operaciones realizadas
// en United Kingdom.
// Equivalencia SQL: WHERE country = 'United Kingdom'
// ============================================================

print("\n========== EJERCICIO 4 ==========");

db.online_retail_ii
    .find({
        country: "United Kingdom"
    })
    .limit(10)
    .forEach(printjson);


// ============================================================
// EJERCICIO 5
// Buscar operaciones cuya cantidad sea superior a 20.
// $gt significa greater than: mayor que.
// Equivalencia SQL: WHERE quantity > 20
// ============================================================

print("\n========== EJERCICIO 5 ==========");

db.online_retail_ii
    .find({
        quantity: { $gt: 20 }
    })
    .limit(10)
    .forEach(printjson);


// ============================================================
// EJERCICIO 6
// Buscar operaciones de United Kingdom cuya cantidad
// sea superior a 20.
// Las dos condiciones deben cumplirse simultaneamente.
// ============================================================

print("\n========== EJERCICIO 6 ==========");

db.online_retail_ii
    .find({
        country: "United Kingdom",
        quantity: { $gt: 20 }
    })
    .limit(10)
    .forEach(printjson);


// ============================================================
// EJERCICIO 7
// Contar cuantas operaciones existen por pais.
//
// $group agrupa por country.
// $sum: 1 cuenta los documentos.
// $sort ordena de mayor a menor.
//
// Equivalencia SQL:
// GROUP BY country
// COUNT(*)
// ORDER BY operaciones DESC
// ============================================================

print("\n========== EJERCICIO 7 ==========");

db.online_retail_ii.aggregate([
    {
        $group: {
            _id: "$country",
            operaciones: { $sum: 1 }
        }
    },
    {
        $sort: {
            operaciones: -1
        }
    }
]).forEach(printjson);


// ============================================================
// EJERCICIO 8
// Obtener los 10 paises con mayor facturacion.
//
// $group agrupa por pais.
// $sum suma total_amount.
// $sort ordena por facturacion.
// $limit devuelve los primeros 10.
// ============================================================

print("\n========== EJERCICIO 8 ==========");

db.online_retail_ii.aggregate([
    {
        $group: {
            _id: "$country",
            facturacion: {
                $sum: "$total_amount"
            }
        }
    },
    {
        $sort: {
            facturacion: -1
        }
    },
    {
        $limit: 10
    }
]).forEach(printjson);


// ============================================================
// EJERCICIO 9
// Obtener estadisticas de ventas para cada pais:
//
//   - numero de operaciones
//   - facturacion total
//   - importe medio
//   - importe minimo
//   - importe maximo
//
// Equivalencias:
// COUNT -> $sum: 1
// SUM   -> $sum
// AVG   -> $avg
// MIN   -> $min
// MAX   -> $max
// ============================================================

print("\n========== EJERCICIO 9 ==========");

db.online_retail_ii.aggregate([
    {
        $group: {
            _id: "$country",
            operaciones: {
                $sum: 1
            },
            facturacion: {
                $sum: "$total_amount"
            },
            importe_medio: {
                $avg: "$total_amount"
            },
            importe_minimo: {
                $min: "$total_amount"
            },
            importe_maximo: {
                $max: "$total_amount"
            }
        }
    },
    {
        $sort: {
            facturacion: -1
        }
    }
]).forEach(printjson);


// ============================================================
// EJERCICIO 10 - RETO FINAL
//
// Obtener los 10 clientes con mayor facturacion.
//
// Para cada cliente mostrar:
//   - customer_id
//   - numero de operaciones
//   - cantidad total de productos
//   - facturacion
//   - importe medio
//
// Excluir customer_id nulos.
//
// Pipeline:
//
// $match
//    |
// $group
//    |
// $sort
//    |
// $limit
// ============================================================

print("\n========== EJERCICIO 10 ==========");

db.online_retail_ii.aggregate([
    {
        $match: {
            customer_id: {
                $ne: null
            }
        }
    },
    {
        $group: {
            _id: "$customer_id",
            operaciones: {
                $sum: 1
            },
            productos: {
                $sum: "$quantity"
            },
            facturacion: {
                $sum: "$total_amount"
            },
            importe_medio: {
                $avg: "$total_amount"
            }
        }
    },
    {
        $sort: {
            facturacion: -1
        }
    },
    {
        $limit: 10
    }
]).forEach(printjson);


print("\n========== FIN DEL TALLER MONGODB ==========");
