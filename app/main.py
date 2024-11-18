from flask import Flask,jsonify
from flask_mysqldb import MySQL
from config import config
from datetime import datetime

app = Flask(__name__)
app.json.sort_keys = False
conexion = MySQL(app)


def formatear_fecha(fecha, formato="%Y-%m-%d"):
    if isinstance(fecha, str):
        try:
            fecha = datetime.strptime(fecha, "%Y-%m-%d")
        except ValueError:
            raise ValueError("El formato de la fecha es incorrecto. Se esperaba 'YYYY-MM-DD'.")
    
    # Formateamos la fecha
    return fecha.strftime(formato)


#GET para generar los gastos
@app.route('/generar_gastos/<mes>/<anio>',methods=['GET'])
def get_gastos(mes,anio):
    try:
        cursor = conexion.connection.cursor()
        sql = "SELECT * FROM detalle_gasto WHERE MONTH(fechaGasto) = '{0}' AND YEAR(fechaGasto) = '{1}'".format(mes,anio)
        cursor.execute(sql)
        datos = cursor.fetchall()
        departamentos=[]
        if datos != None:
            for depto in datos:
                sql = "SELECT piso, numero FROM departamento WHERE id_depto = '{0}'".format(depto[1])
                pagoAgua = int(depto[3]) * 721
                pagoLuz = int(depto[4]) * 192
                cursor.execute(sql)
                detalle_depto = cursor.fetchone()               
                detalle_pago = {'id_depto': depto[0], 'numero_depto': detalle_depto[1],'piso_depto': detalle_depto[0], 'pagoAgua':pagoAgua, 'pagoLuz': pagoLuz, 'totalPorPagar':pagoAgua+pagoLuz}
                departamentos.append(detalle_pago)
            titulo = "Gastos comunes generados para los departamentos en el mes '{0}', año {1}".format(mes,anio)
            return jsonify({'mensaje_detalle': titulo, 'departamentos': departamentos})
        return jsonify({'mensaje': 'No se encontraron datos'})
    except Exception as error:
        return jsonify({'mensaje':'Error al conseguir datos'})

#PUT para pagar una cuota
@app.route('/pagar_cuota/<id_depto>/<fechaAPagar>/<fechaPago>',methods=['PUT'])
def pagar_cuota(id_depto, fechaAPagar,fechaPago):
    try:
        estado_pago = ''
        fechaPagarDate = datetime.strptime(fechaAPagar,"%Y-%m-%d")
        fechaPagoDate = datetime.strptime(fechaPago,"%Y-%m-%d")
        mes = fechaPagarDate.month
        anio = fechaPagarDate.year
        cursor = conexion.connection.cursor()
        sql = "SELECT id_depto, estado_pago FROM detalle_pago WHERE id_depto = '{0}' AND MONTH(fechaAPagar) ='{1}' AND YEAR(fechaAPagar) = '{2}'".format(id_depto,mes,anio)
        cursor.execute(sql)
        estado = cursor.fetchone()
        if estado[1] == "Pagado":
            estado_pago = "Pago duplicado"
            respuesta_pago = {'id_depto': estado[0],'fechaPago':fechaPago,'periodo_pagado':fechaAPagar,'estado_transaccion':estado_pago}
            return jsonify(respuesta_pago)
        else :
            sql = "UPDATE detalle_pago SET fechaPagado = '{0}', estado_pago = 'Pagado' WHERE id_depto = '{1}' AND MONTH(fechaAPagar) ='{2}' AND YEAR(fechaAPagar) = '{3}'".format(fechaPago,id_depto,mes,anio)
            cursor.execute(sql)
            conexion.connection.commit()
            if fechaPagoDate < fechaPagarDate:
                estado_pago = "Pago exitoso dentro del plazo"
            else:
                estado_pago = "Pago exitoso fuera del plazo"
            sql = "SELECT numero FROM departamento WHERE id_depto = '{0}'".format(id_depto)
            cursor.execute(sql)
            detalle_depto = cursor.fetchone()
            respuesta_pago = {'numero_depto': detalle_depto[0],'fechaPago':fechaPago,'periodo_pagado':fechaAPagar,'estado_transaccion':estado_pago}
            return jsonify(respuesta_pago)
    except Exception as error:
        return jsonify({'mensaje':'Error al realizar la transaccion'})

#GET para obtener listado de pagos pendientes
@app.route('/pagos_pendientes/<mes>/<anio>')
def get_pendientes(mes, anio):
        sql = "SELECT * FROM detalle_pago WHERE estado_pago = 'Sin pagar' AND fechaAPagar BETWEEN '{0}-01-01' AND '{0}-{1}-30' ORDER BY fechaAPagar ASC;".format(anio,mes)
        cursor = conexion.connection.cursor()
        cursor.execute(sql)
        datos = cursor.fetchall()
        departamentos = []
        for dpto in datos:
            sql = "SELECT piso, numero FROM departamento WHERE id_depto = '{0}'".format(dpto[1])
            cursor.execute(sql)
            detalle_depto = cursor.fetchone()
            fecha = formatear_fecha(dpto[3])
            detalle_por_pagar = {'piso_depto': detalle_depto[0],'numero_depto':detalle_depto[1], 'fecha_a_pagar': fecha,'monto_a_pagar':dpto[2],'estado':dpto[5]}
            departamentos.append(detalle_por_pagar)
        if not departamentos:
            return jsonify({'respuesta':'Sin montos pendientes'})
        else:
            titulo = "Departamentos con cuentas pendientes hasta el mes '{0}', año {1}".format(mes,anio)
            return jsonify({'titulo': titulo, 'departamentos': departamentos})


@app.route('/', methods=['GET'])
def index():
    return jsonify({'':'Bienvenido'})

if __name__=="__main__":
    app.config.from_object(config['development'])
    app.run()
