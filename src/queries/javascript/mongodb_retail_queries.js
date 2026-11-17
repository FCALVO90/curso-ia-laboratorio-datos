// ============================================================
// MONGODB / MONGOSH - ONLINE RETAIL II
// BASE DE DATOS : curso_ia
// COLECCION     : online_retail_ii
// ============================================================

db = db.getSiblingDB("curso_ia");


// ============================================================
// 01. MUESTRA DEL DATASET
// ============================================================

db.online_retail_ii.find(
    {},
    {
        _id: 0,
        invoice_no: 1,
        stockcode: 1,
        description: 1,
        quantity: 1,
        invoice_date: 1,
        unit_price: 1,
        customer_id: 1,
        country: 1,
        hoja_origen: 1,
        is_cancelled: 1,
        total_amount: 1,
        year: 1,
        month: 1,
        day: 1,
        hour: 1
    }
)
.sort({ invoice_date: -1 })
.limit(20)
.forEach(function (documento) {
    print(EJSON.stringify(documento, null, 0));
});


// ============================================================
// 02. RESUMEN GENERAL DEL DATASET
// ============================================================

db.online_retail_ii.aggregate([
    {
        $group: {
            _id: null,
            total_lineas: { $sum: 1 },
            facturas: { $addToSet: "$invoice_no" },
            productos: { $addToSet: "$stockcode" },
            clientes: { $addToSet: "$customer_id" },
            paises: { $addToSet: "$country" },
            primera_fecha: { $min: "$invoice_date" },
            ultima_fecha: { $max: "$invoice_date" },
            facturacion_total: { $sum: "$total_amount" }
        }
    },
    {
        $project: {
            _id: 0,
            total_lineas: 1,
            total_facturas: { $size: "$facturas" },
            total_productos: { $size: "$productos" },
            total_clientes: { $size: "$clientes" },
            total_paises: { $size: "$paises" },
            primera_fecha: 1,
            ultima_fecha: 1,
            facturacion_total: { $round: ["$facturacion_total", 2] }
        }
    }
])
.forEach(function (documento) {
    print(EJSON.stringify(documento, null, 0));
});


// ============================================================
// 03. CALIDAD DE DATOS - NULOS
// ============================================================

db.online_retail_ii.aggregate([
    {
        $group: {
            _id: null,

            total_filas: { $sum: 1 },

            invoice_no_nulos: {
                $sum: {
                    $cond: [
                        { $eq: [{ $ifNull: ["$invoice_no", null] }, null] },
                        1,
                        0
                    ]
                }
            },

            stockcode_nulos: {
                $sum: {
                    $cond: [
                        { $eq: [{ $ifNull: ["$stockcode", null] }, null] },
                        1,
                        0
                    ]
                }
            },

            description_nulos: {
                $sum: {
                    $cond: [
                        { $eq: [{ $ifNull: ["$description", null] }, null] },
                        1,
                        0
                    ]
                }
            },

            quantity_nulos: {
                $sum: {
                    $cond: [
                        { $eq: [{ $ifNull: ["$quantity", null] }, null] },
                        1,
                        0
                    ]
                }
            },

            invoice_date_nulos: {
                $sum: {
                    $cond: [
                        { $eq: [{ $ifNull: ["$invoice_date", null] }, null] },
                        1,
                        0
                    ]
                }
            },

            unit_price_nulos: {
                $sum: {
                    $cond: [
                        { $eq: [{ $ifNull: ["$unit_price", null] }, null] },
                        1,
                        0
                    ]
                }
            },

            customer_id_nulos: {
                $sum: {
                    $cond: [
                        { $eq: [{ $ifNull: ["$customer_id", null] }, null] },
                        1,
                        0
                    ]
                }
            },

            country_nulos: {
                $sum: {
                    $cond: [
                        { $eq: [{ $ifNull: ["$country", null] }, null] },
                        1,
                        0
                    ]
                }
            },

            total_amount_nulos: {
                $sum: {
                    $cond: [
                        { $eq: [{ $ifNull: ["$total_amount", null] }, null] },
                        1,
                        0
                    ]
                }
            }
        }
    },
    {
        $project: {
            _id: 0
        }
    }
])
.forEach(function (documento) {
    print(EJSON.stringify(documento, null, 0));
});


// ============================================================
// 04. CALIDAD DE DATOS - VALORES ANOMALOS
// ============================================================

db.online_retail_ii.aggregate([
    {
        $group: {
            _id: null,

            total_filas: { $sum: 1 },

            cantidad_negativa: {
                $sum: {
                    $cond: [{ $lt: ["$quantity", 0] }, 1, 0]
                }
            },

            cantidad_cero: {
                $sum: {
                    $cond: [{ $eq: ["$quantity", 0] }, 1, 0]
                }
            },

            precio_negativo: {
                $sum: {
                    $cond: [{ $lt: ["$unit_price", 0] }, 1, 0]
                }
            },

            precio_cero: {
                $sum: {
                    $cond: [{ $eq: ["$unit_price", 0] }, 1, 0]
                }
            },

            importe_negativo: {
                $sum: {
                    $cond: [{ $lt: ["$total_amount", 0] }, 1, 0]
                }
            },

            lineas_canceladas: {
                $sum: {
                    $cond: [{ $eq: ["$is_cancelled", 1] }, 1, 0]
                }
            }
        }
    },
    {
        $project: { _id: 0 }
    }
])
.forEach(function (documento) {
    print(EJSON.stringify(documento, null, 0));
});


// ============================================================
// 05. FACTURACION POR PAIS
// ============================================================

db.online_retail_ii.aggregate([
    {
        $match: {
            is_cancelled: 0,
            quantity: { $gt: 0 },
            total_amount: { $gt: 0 }
        }
    },
    {
        $group: {
            _id: "$country",
            total_lineas: { $sum: 1 },
            facturas: { $addToSet: "$invoice_no" },
            clientes: { $addToSet: "$customer_id" },
            unidades: { $sum: "$quantity" },
            facturacion: { $sum: "$total_amount" }
        }
    },
    {
        $project: {
            _id: 0,
            country: "$_id",
            total_lineas: 1,
            total_facturas: { $size: "$facturas" },
            total_clientes: { $size: "$clientes" },
            unidades: 1,
            facturacion: { $round: ["$facturacion", 2] }
        }
    },
    { $sort: { facturacion: -1 } }
])
.forEach(function (documento) {
    print(EJSON.stringify(documento, null, 0));
});


// ============================================================
// 06. TOP 20 PRODUCTOS POR FACTURACION
// ============================================================

db.online_retail_ii.aggregate([
    {
        $match: {
            is_cancelled: 0,
            quantity: { $gt: 0 },
            total_amount: { $gt: 0 }
        }
    },
    {
        $group: {
            _id: {
                stockcode: "$stockcode",
                description: "$description"
            },
            unidades_vendidas: { $sum: "$quantity" },
            facturas: { $addToSet: "$invoice_no" },
            precio_medio: { $avg: "$unit_price" },
            facturacion: { $sum: "$total_amount" }
        }
    },
    {
        $project: {
            _id: 0,
            stockcode: "$_id.stockcode",
            description: "$_id.description",
            unidades_vendidas: 1,
            numero_facturas: { $size: "$facturas" },
            precio_medio: { $round: ["$precio_medio", 2] },
            facturacion: { $round: ["$facturacion", 2] }
        }
    },
    { $sort: { facturacion: -1 } },
    { $limit: 20 }
])
.forEach(function (documento) {
    print(EJSON.stringify(documento, null, 0));
});


// ============================================================
// 07. TOP 20 PRODUCTOS POR UNIDADES
// ============================================================

db.online_retail_ii.aggregate([
    {
        $match: {
            is_cancelled: 0,
            quantity: { $gt: 0 }
        }
    },
    {
        $group: {
            _id: {
                stockcode: "$stockcode",
                description: "$description"
            },
            unidades_vendidas: { $sum: "$quantity" },
            facturacion: { $sum: "$total_amount" }
        }
    },
    {
        $project: {
            _id: 0,
            stockcode: "$_id.stockcode",
            description: "$_id.description",
            unidades_vendidas: 1,
            facturacion: { $round: ["$facturacion", 2] }
        }
    },
    { $sort: { unidades_vendidas: -1 } },
    { $limit: 20 }
])
.forEach(function (documento) {
    print(EJSON.stringify(documento, null, 0));
});


// ============================================================
// 08. TOP 20 CLIENTES
// ============================================================

db.online_retail_ii.aggregate([
    {
        $match: {
            customer_id: { $ne: null },
            is_cancelled: 0,
            quantity: { $gt: 0 },
            total_amount: { $gt: 0 }
        }
    },
    {
        $group: {
            _id: "$customer_id",
            facturas: { $addToSet: "$invoice_no" },
            productos: { $addToSet: "$stockcode" },
            unidades: { $sum: "$quantity" },
            facturacion: { $sum: "$total_amount" }
        }
    },
    {
        $project: {
            _id: 0,
            customer_id: "$_id",
            numero_facturas: { $size: "$facturas" },
            productos_distintos: { $size: "$productos" },
            unidades: 1,
            facturacion: { $round: ["$facturacion", 2] }
        }
    },
    { $sort: { facturacion: -1 } },
    { $limit: 20 }
])
.forEach(function (documento) {
    print(EJSON.stringify(documento, null, 0));
});


// ============================================================
// 09. FACTURACION ANUAL
// ============================================================

db.online_retail_ii.aggregate([
    {
        $match: {
            is_cancelled: 0,
            quantity: { $gt: 0 },
            total_amount: { $gt: 0 }
        }
    },
    {
        $group: {
            _id: "$year",
            facturas: { $addToSet: "$invoice_no" },
            clientes: { $addToSet: "$customer_id" },
            unidades: { $sum: "$quantity" },
            facturacion: { $sum: "$total_amount" }
        }
    },
    {
        $project: {
            _id: 0,
            anio: "$_id",
            facturas: { $size: "$facturas" },
            clientes: { $size: "$clientes" },
            unidades: 1,
            facturacion: { $round: ["$facturacion", 2] }
        }
    },
    { $sort: { anio: 1 } }
])
.forEach(function (documento) {
    print(EJSON.stringify(documento, null, 0));
});


// ============================================================
// 10. FACTURACION MENSUAL
// ============================================================

db.online_retail_ii.aggregate([
    {
        $match: {
            is_cancelled: 0,
            quantity: { $gt: 0 },
            total_amount: { $gt: 0 }
        }
    },
    {
        $group: {
            _id: {
                anio: "$year",
                mes: "$month"
            },
            facturas: { $addToSet: "$invoice_no" },
            clientes: { $addToSet: "$customer_id" },
            unidades: { $sum: "$quantity" },
            facturacion: { $sum: "$total_amount" }
        }
    },
    {
        $project: {
            _id: 0,
            anio: "$_id.anio",
            mes: "$_id.mes",
            facturas: { $size: "$facturas" },
            clientes: { $size: "$clientes" },
            unidades: 1,
            facturacion: { $round: ["$facturacion", 2] }
        }
    },
    { $sort: { anio: 1, mes: 1 } }
])
.forEach(function (documento) {
    print(EJSON.stringify(documento, null, 0));
});


// ============================================================
// 11. FACTURACION POR ANIO Y MES
// ============================================================

db.online_retail_ii.aggregate([
    {
        $match: {
            is_cancelled: 0,
            quantity: { $gt: 0 },
            total_amount: { $gt: 0 }
        }
    },
    {
        $group: {
            _id: {
                anio: "$year",
                mes: "$month"
            },
            facturas: { $addToSet: "$invoice_no" },
            unidades: { $sum: "$quantity" },
            facturacion: { $sum: "$total_amount" }
        }
    },
    {
        $project: {
            _id: 0,
            anio: "$_id.anio",
            mes: "$_id.mes",
            facturas: { $size: "$facturas" },
            unidades: 1,
            facturacion: { $round: ["$facturacion", 2] }
        }
    },
    { $sort: { anio: 1, mes: 1 } }
])
.forEach(function (documento) {
    print(EJSON.stringify(documento, null, 0));
});


// ============================================================
// 12. ACTIVIDAD POR HORA
// ============================================================

db.online_retail_ii.aggregate([
    {
        $match: {
            is_cancelled: 0,
            quantity: { $gt: 0 },
            total_amount: { $gt: 0 }
        }
    },
    {
        $group: {
            _id: "$hour",
            facturas: { $addToSet: "$invoice_no" },
            lineas: { $sum: 1 },
            unidades: { $sum: "$quantity" },
            facturacion: { $sum: "$total_amount" }
        }
    },
    {
        $project: {
            _id: 0,
            hora: "$_id",
            facturas: { $size: "$facturas" },
            lineas: 1,
            unidades: 1,
            facturacion: { $round: ["$facturacion", 2] }
        }
    },
    { $sort: { hora: 1 } }
])
.forEach(function (documento) {
    print(EJSON.stringify(documento, null, 0));
});


// ============================================================
// 13. ANALISIS DE CANCELACIONES
// ============================================================

db.online_retail_ii.aggregate([
    {
        $group: {
            _id: "$is_cancelled",
            lineas: { $sum: 1 },
            facturas: { $addToSet: "$invoice_no" },
            cantidad: { $sum: "$quantity" },
            importe: { $sum: "$total_amount" }
        }
    },
    {
        $project: {
            _id: 0,
            is_cancelled: "$_id",
            lineas: 1,
            facturas: { $size: "$facturas" },
            cantidad: 1,
            importe: { $round: ["$importe", 2] }
        }
    },
    { $sort: { is_cancelled: 1 } }
])
.forEach(function (documento) {
    print(EJSON.stringify(documento, null, 0));
});


// ============================================================
// 14. CANCELACIONES POR PAIS
// ============================================================

db.online_retail_ii.aggregate([
    {
        $match: {
            is_cancelled: 1
        }
    },
    {
        $group: {
            _id: "$country",
            lineas_canceladas: { $sum: 1 },
            facturas_canceladas: { $addToSet: "$invoice_no" },
            importe_cancelado: { $sum: "$total_amount" }
        }
    },
    {
        $project: {
            _id: 0,
            country: "$_id",
            lineas_canceladas: 1,
            facturas_canceladas: {
                $size: "$facturas_canceladas"
            },
            importe_cancelado: {
                $round: ["$importe_cancelado", 2]
            }
        }
    },
    { $sort: { lineas_canceladas: -1 } }
])
.forEach(function (documento) {
    print(EJSON.stringify(documento, null, 0));
});


// ============================================================
// 15. DEVOLUCIONES
// ============================================================

db.online_retail_ii.find(
    {
        quantity: { $lt: 0 }
    },
    {
        _id: 0,
        invoice_no: 1,
        invoice_date: 1,
        customer_id: 1,
        stockcode: 1,
        description: 1,
        country: 1,
        quantity: 1,
        unit_price: 1,
        total_amount: 1,
        is_cancelled: 1
    }
)
.sort({ invoice_date: -1 })
.limit(100)
.forEach(function (documento) {
    print(EJSON.stringify(documento, null, 0));
});


// ============================================================
// 16. TICKET POR FACTURA
// ============================================================

db.online_retail_ii.aggregate([
    {
        $match: {
            is_cancelled: 0,
            quantity: { $gt: 0 },
            total_amount: { $gt: 0 }
        }
    },
    {
        $group: {
            _id: {
                invoice_no: "$invoice_no",
                customer_id: "$customer_id",
                country: "$country"
            },
            fecha_factura: { $min: "$invoice_date" },
            unidades: { $sum: "$quantity" },
            lineas: { $sum: 1 },
            productos: { $addToSet: "$stockcode" },
            total_factura: { $sum: "$total_amount" }
        }
    },
    {
        $project: {
            _id: 0,
            invoice_no: "$_id.invoice_no",
            customer_id: "$_id.customer_id",
            country: "$_id.country",
            fecha_factura: 1,
            unidades: 1,
            lineas: 1,
            productos_distintos: { $size: "$productos" },
            total_factura: { $round: ["$total_factura", 2] }
        }
    },
    { $sort: { total_factura: -1 } },
    { $limit: 50 }
])
.forEach(function (documento) {
    print(EJSON.stringify(documento, null, 0));
});


// ============================================================
// 17. TICKET MEDIO
// ============================================================

db.online_retail_ii.aggregate([
    {
        $match: {
            is_cancelled: 0,
            quantity: { $gt: 0 },
            total_amount: { $gt: 0 }
        }
    },
    {
        $group: {
            _id: "$invoice_no",
            total_factura: { $sum: "$total_amount" }
        }
    },
    {
        $group: {
            _id: null,
            numero_facturas: { $sum: 1 },
            ticket_medio: { $avg: "$total_factura" },
            ticket_minimo: { $min: "$total_factura" },
            ticket_maximo: { $max: "$total_factura" }
        }
    },
    {
        $project: {
            _id: 0,
            numero_facturas: 1,
            ticket_medio: { $round: ["$ticket_medio", 2] },
            ticket_minimo: { $round: ["$ticket_minimo", 2] },
            ticket_maximo: { $round: ["$ticket_maximo", 2] }
        }
    }
])
.forEach(function (documento) {
    print(EJSON.stringify(documento, null, 0));
});


// ============================================================
// 18. TICKET MEDIO POR PAIS
// ============================================================

db.online_retail_ii.aggregate([
    {
        $match: {
            is_cancelled: 0,
            quantity: { $gt: 0 },
            total_amount: { $gt: 0 }
        }
    },
    {
        $group: {
            _id: {
                country: "$country",
                invoice_no: "$invoice_no"
            },
            total_factura: { $sum: "$total_amount" }
        }
    },
    {
        $group: {
            _id: "$_id.country",
            numero_facturas: { $sum: 1 },
            ticket_medio: { $avg: "$total_factura" },
            facturacion: { $sum: "$total_factura" }
        }
    },
    {
        $project: {
            _id: 0,
            country: "$_id",
            numero_facturas: 1,
            ticket_medio: { $round: ["$ticket_medio", 2] },
            facturacion: { $round: ["$facturacion", 2] }
        }
    },
    { $sort: { facturacion: -1 } }
])
.forEach(function (documento) {
    print(EJSON.stringify(documento, null, 0));
});


// ============================================================
// 19. CLIENTES POR PAIS
// ============================================================

db.online_retail_ii.aggregate([
    {
        $match: {
            customer_id: { $ne: null },
            is_cancelled: 0,
            total_amount: { $gt: 0 }
        }
    },
    {
        $group: {
            _id: "$country",
            clientes: { $addToSet: "$customer_id" },
            facturas: { $addToSet: "$invoice_no" },
            facturacion: { $sum: "$total_amount" }
        }
    },
    {
        $project: {
            _id: 0,
            country: "$_id",
            clientes: { $size: "$clientes" },
            facturas: { $size: "$facturas" },
            facturacion: { $round: ["$facturacion", 2] }
        }
    },
    { $sort: { clientes: -1 } }
])
.forEach(function (documento) {
    print(EJSON.stringify(documento, null, 0));
});


// ============================================================
// 20. TOP 5 PRODUCTOS POR PAIS
// EQUIVALENTE A ROW_NUMBER() PARTITION BY
// ============================================================

db.online_retail_ii.aggregate([
    {
        $match: {
            is_cancelled: 0,
            quantity: { $gt: 0 },
            total_amount: { $gt: 0 }
        }
    },
    {
        $group: {
            _id: {
                country: "$country",
                stockcode: "$stockcode",
                description: "$description"
            },
            unidades_vendidas: { $sum: "$quantity" },
            facturacion: { $sum: "$total_amount" }
        }
    },
    {
        $project: {
            _id: 0,
            country: "$_id.country",
            stockcode: "$_id.stockcode",
            description: "$_id.description",
            unidades_vendidas: 1,
            facturacion: 1
        }
    },
    {
        $setWindowFields: {
            partitionBy: "$country",
            sortBy: {
                facturacion: -1
            },
            output: {
                posicion: {
                    $documentNumber: {}
                }
            }
        }
    },
    {
        $match: {
            posicion: { $lte: 5 }
        }
    },
    {
        $project: {
            country: 1,
            posicion: 1,
            stockcode: 1,
            description: 1,
            unidades_vendidas: 1,
            facturacion: { $round: ["$facturacion", 2] }
        }
    },
    {
        $sort: {
            country: 1,
            posicion: 1
        }
    }
])
.forEach(function (documento) {
    print(EJSON.stringify(documento, null, 0));
});


// ============================================================
// 21. RANKING DE PAISES
// ============================================================

db.online_retail_ii.aggregate([
    {
        $match: {
            is_cancelled: 0,
            quantity: { $gt: 0 },
            total_amount: { $gt: 0 }
        }
    },
    {
        $group: {
            _id: "$country",
            facturacion: { $sum: "$total_amount" }
        }
    },
    {
        $project: {
            _id: 0,
            country: "$_id",
            facturacion: 1
        }
    },
    {
        $setWindowFields: {
            sortBy: {
                facturacion: -1
            },
            output: {
                posicion: {
                    $denseRank: {}
                }
            }
        }
    },
    {
        $project: {
            posicion: 1,
            country: 1,
            facturacion: { $round: ["$facturacion", 2] }
        }
    },
    { $sort: { posicion: 1 } }
])
.forEach(function (documento) {
    print(EJSON.stringify(documento, null, 0));
});


// ============================================================
// 22. EVOLUCION MENSUAL CON MES ANTERIOR
// EQUIVALENTE A LAG()
// ============================================================

db.online_retail_ii.aggregate([
    {
        $match: {
            is_cancelled: 0,
            quantity: { $gt: 0 },
            total_amount: { $gt: 0 }
        }
    },
    {
        $group: {
            _id: {
                anio: "$year",
                mes: "$month"
            },
            facturacion: { $sum: "$total_amount" }
        }
    },
    {
        $project: {
            _id: 0,
            anio: "$_id.anio",
            mes: "$_id.mes",
            periodo: {
                $add: [
                    { $multiply: ["$_id.anio", 100] },
                    "$_id.mes"
                ]
            },
            facturacion: 1
        }
    },
    {
        $setWindowFields: {
            sortBy: {
                periodo: 1
            },
            output: {
                facturacion_mes_anterior: {
                    $shift: {
                        output: "$facturacion",
                        by: -1,
                        default: null
                    }
                }
            }
        }
    },
    {
        $project: {
            _id: 0,
            anio: 1,
            mes: 1,
            facturacion: { $round: ["$facturacion", 2] },
            facturacion_mes_anterior: {
                $round: ["$facturacion_mes_anterior", 2]
            }
        }
    },
    { $sort: { anio: 1, mes: 1 } }
])
.forEach(function (documento) {
    print(EJSON.stringify(documento, null, 0));
});


// ============================================================
// 23. CRECIMIENTO MENSUAL PORCENTUAL
// ============================================================

db.online_retail_ii.aggregate([
    {
        $match: {
            is_cancelled: 0,
            quantity: { $gt: 0 },
            total_amount: { $gt: 0 }
        }
    },
    {
        $group: {
            _id: {
                anio: "$year",
                mes: "$month"
            },
            facturacion: { $sum: "$total_amount" }
        }
    },
    {
        $project: {
            _id: 0,
            anio: "$_id.anio",
            mes: "$_id.mes",
            periodo: {
                $add: [
                    { $multiply: ["$_id.anio", 100] },
                    "$_id.mes"
                ]
            },
            facturacion: 1
        }
    },
    {
        $setWindowFields: {
            sortBy: {
                periodo: 1
            },
            output: {
                facturacion_anterior: {
                    $shift: {
                        output: "$facturacion",
                        by: -1,
                        default: null
                    }
                }
            }
        }
    },
    {
        $project: {
            _id: 0,
            anio: 1,
            mes: 1,
            facturacion: {
                $round: ["$facturacion", 2]
            },
            facturacion_anterior: {
                $round: ["$facturacion_anterior", 2]
            },
            crecimiento_porcentaje: {
                $cond: [
                    {
                        $or: [
                            { $eq: ["$facturacion_anterior", null] },
                            { $eq: ["$facturacion_anterior", 0] }
                        ]
                    },
                    null,
                    {
                        $round: [
                            {
                                $multiply: [
                                    {
                                        $divide: [
                                            {
                                                $subtract: [
                                                    "$facturacion",
                                                    "$facturacion_anterior"
                                                ]
                                            },
                                            "$facturacion_anterior"
                                        ]
                                    },
                                    100
                                ]
                            },
                            2
                        ]
                    }
                ]
            }
        }
    },
    { $sort: { anio: 1, mes: 1 } }
])
.forEach(function (documento) {
    print(EJSON.stringify(documento, null, 0));
});


// ============================================================
// 24. FACTURACION ACUMULADA
// ============================================================

db.online_retail_ii.aggregate([
    {
        $match: {
            is_cancelled: 0,
            quantity: { $gt: 0 },
            total_amount: { $gt: 0 }
        }
    },
    {
        $group: {
            _id: {
                anio: "$year",
                mes: "$month"
            },
            facturacion: { $sum: "$total_amount" }
        }
    },
    {
        $project: {
            _id: 0,
            anio: "$_id.anio",
            mes: "$_id.mes",
            periodo: {
                $add: [
                    { $multiply: ["$_id.anio", 100] },
                    "$_id.mes"
                ]
            },
            facturacion: 1
        }
    },
    {
        $setWindowFields: {
            sortBy: {
                periodo: 1
            },
            output: {
                facturacion_acumulada: {
                    $sum: "$facturacion",
                    window: {
                        documents: ["unbounded", "current"]
                    }
                }
            }
        }
    },
    {
        $project: {
            _id: 0,
            anio: 1,
            mes: 1,
            facturacion_mensual: {
                $round: ["$facturacion", 2]
            },
            facturacion_acumulada: {
                $round: ["$facturacion_acumulada", 2]
            }
        }
    },
    { $sort: { anio: 1, mes: 1 } }
])
.forEach(function (documento) {
    print(EJSON.stringify(documento, null, 0));
});


// ============================================================
// 25. RANKING GLOBAL DE CLIENTES
// ============================================================

db.online_retail_ii.aggregate([
    {
        $match: {
            customer_id: { $ne: null },
            is_cancelled: 0,
            quantity: { $gt: 0 },
            total_amount: { $gt: 0 }
        }
    },
    {
        $group: {
            _id: "$customer_id",
            facturas: { $addToSet: "$invoice_no" },
            facturacion: { $sum: "$total_amount" }
        }
    },
    {
        $project: {
            _id: 0,
            customer_id: "$_id",
            facturas: { $size: "$facturas" },
            facturacion: 1
        }
    },
    {
        $setWindowFields: {
            sortBy: {
                facturacion: -1
            },
            output: {
                posicion: {
                    $documentNumber: {}
                }
            }
        }
    },
    {
        $project: {
            posicion: 1,
            customer_id: 1,
            facturas: 1,
            facturacion: { $round: ["$facturacion", 2] }
        }
    },
    { $limit: 100 }
])
.forEach(function (documento) {
    print(EJSON.stringify(documento, null, 0));
});


// ============================================================
// 26. CLIENTES RECURRENTES
// ============================================================

db.online_retail_ii.aggregate([
    {
        $match: {
            customer_id: { $ne: null },
            is_cancelled: 0,
            quantity: { $gt: 0 },
            total_amount: { $gt: 0 }
        }
    },
    {
        $group: {
            _id: "$customer_id",
            facturas: { $addToSet: "$invoice_no" },
            primera_compra: { $min: "$invoice_date" },
            ultima_compra: { $max: "$invoice_date" },
            facturacion_total: { $sum: "$total_amount" }
        }
    },
    {
        $project: {
            _id: 0,
            customer_id: "$_id",
            numero_facturas: { $size: "$facturas" },
            primera_compra: 1,
            ultima_compra: 1,
            facturacion_total: {
                $round: ["$facturacion_total", 2]
            }
        }
    },
    {
        $match: {
            numero_facturas: { $gt: 1 }
        }
    },
    { $sort: { numero_facturas: -1 } }
])
.forEach(function (documento) {
    print(EJSON.stringify(documento, null, 0));
});


// ============================================================
// 27. RESUMEN POR HOJA DE ORIGEN
// ============================================================

db.online_retail_ii.aggregate([
    {
        $group: {
            _id: "$hoja_origen",
            total_lineas: { $sum: 1 },
            facturas: { $addToSet: "$invoice_no" },
            clientes: { $addToSet: "$customer_id" },
            productos: { $addToSet: "$stockcode" },
            primera_fecha: { $min: "$invoice_date" },
            ultima_fecha: { $max: "$invoice_date" },
            importe_total: { $sum: "$total_amount" }
        }
    },
    {
        $project: {
            _id: 0,
            hoja_origen: "$_id",
            total_lineas: 1,
            facturas: { $size: "$facturas" },
            clientes: { $size: "$clientes" },
            productos: { $size: "$productos" },
            primera_fecha: 1,
            ultima_fecha: 1,
            importe_total: { $round: ["$importe_total", 2] }
        }
    },
    { $sort: { hoja_origen: 1 } }
])
.forEach(function (documento) {
    print(EJSON.stringify(documento, null, 0));
});


// ============================================================
// 28. DISTRIBUCION DE PRECIOS
// ============================================================

db.online_retail_ii.aggregate([
    {
        $match: {
            unit_price: { $gt: 0 }
        }
    },
    {
        $group: {
            _id: null,
            numero_registros: { $sum: 1 },
            precio_minimo: { $min: "$unit_price" },
            precio_medio: { $avg: "$unit_price" },
            precio_maximo: { $max: "$unit_price" }
        }
    },
    {
        $project: {
            _id: 0,
            numero_registros: 1,
            precio_minimo: { $round: ["$precio_minimo", 2] },
            precio_medio: { $round: ["$precio_medio", 2] },
            precio_maximo: { $round: ["$precio_maximo", 2] }
        }
    }
])
.forEach(function (documento) {
    print(EJSON.stringify(documento, null, 0));
});


// ============================================================
// 29. TOP 20 PRECIOS UNITARIOS
// ============================================================

db.online_retail_ii.find(
    {
        unit_price: { $gt: 0 }
    },
    {
        _id: 0,
        stockcode: 1,
        description: 1,
        unit_price: 1,
        invoice_no: 1,
        invoice_date: 1,
        country: 1
    }
)
.sort({ unit_price: -1 })
.limit(20)
.forEach(function (documento) {
    print(EJSON.stringify(documento, null, 0));
});


// ============================================================
// 30. RESUMEN FINAL POR ANIO
// ============================================================

db.online_retail_ii.aggregate([
    {
        $group: {
            _id: "$year",

            lineas: {
                $sum: 1
            },

            facturas: {
                $addToSet: "$invoice_no"
            },

            clientes: {
                $addToSet: "$customer_id"
            },

            productos: {
                $addToSet: "$stockcode"
            },

            paises: {
                $addToSet: "$country"
            },

            unidades_vendidas: {
                $sum: {
                    $cond: [
                        {
                            $and: [
                                { $eq: ["$is_cancelled", 0] },
                                { $gt: ["$quantity", 0] }
                            ]
                        },
                        "$quantity",
                        0
                    ]
                }
            },

            facturas_canceladas_array: {
                $addToSet: {
                    $cond: [
                        { $eq: ["$is_cancelled", 1] },
                        "$invoice_no",
                        null
                    ]
                }
            },

            facturacion: {
                $sum: {
                    $cond: [
                        {
                            $and: [
                                { $eq: ["$is_cancelled", 0] },
                                { $gt: ["$total_amount", 0] }
                            ]
                        },
                        "$total_amount",
                        0
                    ]
                }
            }
        }
    },

    {
        $project: {
            _id: 0,
            anio: "$_id",
            lineas: 1,
            facturas: { $size: "$facturas" },
            clientes: { $size: "$clientes" },
            productos: { $size: "$productos" },
            paises: { $size: "$paises" },
            unidades_vendidas: 1,

            facturas_canceladas: {
                $size: {
                    $setDifference: [
                        "$facturas_canceladas_array",
                        [null]
                    ]
                }
            },

            facturacion: {
                $round: ["$facturacion", 2]
            }
        }
    },

    { $sort: { anio: 1 } }
])
.forEach(function (documento) {
    print(EJSON.stringify(documento, null, 0));
});


// ============================================================
// FIN MONGODB / MONGOSH
// ============================================================
