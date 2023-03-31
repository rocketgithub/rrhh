# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError
import xlwt
import base64
import io
import logging
import time
import datetime
from datetime import date
from datetime import datetime, date, time
from odoo.fields import Date, Datetime
import itertools
from dateutil.relativedelta import relativedelta
import odoo.addons.l10n_gt_extra.a_letras as a_letras

class rrhh_informe_empleador(models.TransientModel):
    _name = 'rrhh.informe_empleador'

    anio = fields.Integer('Año', required=True)
    name = fields.Char('Nombre archivo', size=32)
    archivo = fields.Binary('Archivo', filters='.xls')

    def _get_empleado(self,id):
        empleado_id = self.env['hr.employee'].search([('id', '=', id)])
        return empleado_id

    def _get_salario_promedio(self,id):
        extra_ordinario_total = 0
        historial_salario = []
        salario_meses = {}
        salario_total = 0
        salarios = {'salario_promedio': 0,'totales': 0, 'mes': {}}
        empleado_id = self._get_empleado(id)
        if empleado_id.contract_ids[0].historial_salario_ids:
            for linea in empleado_id.contract_ids[0].historial_salario_ids:
                historial_salario.append({'salario': linea.salario, 'fecha':linea.fecha})

            historial_salario_ordenado = sorted(historial_salario, key=lambda k: k['fecha'],reverse=True)
            fecha_inicio_contrato = datetime.strptime(empleado_id.contract_ids[0].date_start,"%Y-%m-%d")
            fecha_final_contrato = datetime.strptime(empleado_id.contract_id.date_end,"%Y-%m-%d") + relativedelta(months=-1)
            meses_laborados = (fecha_final_contrato.year - fecha_inicio_contrato.year) * 12 + (fecha_final_contrato.month - fecha_inicio_contrato.month)
            contador_mes = 0
            if meses_laborados >= 6:
                while contador_mes < 6:
                    logging.warn('1')
                    mes = relativedelta(months=contador_mes)
                    resta_mes = fecha_final_contrato - mes
                    mes_letras = a_letras.mes_a_letras(resta_mes.month-1)
                    llave = '01-'+str(resta_mes.month)+'-'+str(resta_mes.year)
                    salario_meses[llave] = {'nombre':mes_letras.upper(),'salario': 0,'anio':resta_mes.year,'mes_numero':resta_mes.month-1,'extra':0,'total':0}
                    contador_mes += 1
            else:
                while contador_mes <= meses_laborados:
                    logging.warn('2')
                    mes = relativedelta(months=contador_mes)
                    resta_mes = fecha_final_contrato - mes
                    mes_letras = a_letras.mes_a_letras(resta_mes.month-1)
                    llave = '01-'+str(resta_mes.month)+'-'+str(resta_mes.year)
                    salario_meses[llave] = {'nombre':mes_letras.upper(),'salario': 0,'anio':resta_mes.year,'mes_numero':resta_mes.month-1,'extra':0,'total':0}
                    contador_mes += 1

            contador_mes = 0
            fecha_inicio_diferencia = datetime.strptime(str(historial_salario_ordenado[0]['fecha']), '%Y-%m-%d')
            diferencia_meses = (fecha_final_contrato.year - fecha_inicio_diferencia.year) * 12 + (fecha_final_contrato.month - fecha_inicio_diferencia.month)

            posicion_siguiente = 0
            for linea in historial_salario_ordenado:
                contador = 0
                condicion = False
                if posicion_siguiente == 0:
                    diferencia_meses += 1
                while contador < (diferencia_meses):

                    mes = relativedelta(months=contador_mes)
                    resta_mes = fecha_final_contrato - mes
                    mes_letras = a_letras.mes_a_letras(resta_mes.month-1)
                    llave = '01-'+str(resta_mes.month)+'-'+str(resta_mes.year)
                    if llave in salario_meses:
                        salario_meses[llave]['salario'] = linea['salario']
                        salario_meses[llave]['total'] +=  linea['salario']
                        salario_total += linea['salario']
                    contador += 1
                    contador_mes += 1

                if len(historial_salario_ordenado) > 1:
                    fecha_cambio_salario = datetime.strptime(str(linea['fecha']), '%Y-%m-%d')

                    posicion_siguiente = historial_salario_ordenado.index(linea) + 1
                    if posicion_siguiente < len(historial_salario_ordenado):
                        fecha_inicio_diferencia = datetime.strptime(str(historial_salario_ordenado[posicion_siguiente]['fecha']), '%Y-%m-%d')
                        diferencia_meses = (fecha_cambio_salario.year - fecha_inicio_diferencia.year) * 12 + (fecha_cambio_salario.month - fecha_inicio_diferencia.month)


            nomina_ids = self.env['hr.payslip'].search([('employee_id', '=', empleado_id.id)], order='date_to asc')
            if nomina_ids:
                for nomina in nomina_ids:
                    fecha_fin_nomina = datetime.strptime(str(nomina.date_to),'%Y-%m-%d')
                    mes_nomina = fecha_fin_nomina.month
                    anio_nomina = fecha_fin_nomina.year
                    llave = '01-'+str(mes_nomina)+'-'+str(anio_nomina)
                    extra_ordinario_ids = nomina.company_id.extra_ordinario_ids
                    if llave in salario_meses:
                        for linea in nomina.line_ids:
                            if linea.salary_rule_id.id in extra_ordinario_ids.ids:
                                salario_meses[llave]['extra'] += linea.total
                                salario_meses[llave]['total'] += linea.total
                                extra_ordinario_total += linea.total

        salario_meses = sorted(salario_meses.items(), key = lambda x:datetime.strptime(x[0], '%d-%m-%Y'))

        salarios['totales'] = salario_total
        salarios['extra_ordinario_total'] = extra_ordinario_total
        salarios['total_total'] =  (salario_total + extra_ordinario_total)

        salarios['total_promedio'] = salario_total / len(salario_meses)
        salarios['extra_ordinario_promedio'] = extra_ordinario_total / len(salario_meses)
        salarios['total_salario_promedio'] = salarios['total_total'] / len(salario_meses)
        return {'salarios': salarios,'meses_salarios': salario_meses}

    def _get_dias_laborados(self,id):
        empleado_id = self._get_empleado(id)
        dias = datetime.strptime( str(empleado_id.contract_ids[0].date_end),"%Y-%m-%d") - datetime.strptime(str(empleado_id.contract_ids[0].date_start),"%Y-%m-%d")
        return dias.days+1

    def _get_indemnizacion(self,id):
        dias_laborados = 0
        salario_promedio = 0
        indemnizacion = 0
        regla_76_78 = 0
        regla_42_92 = 0
        indemnizacion = 0
        empleado_id = self._get_empleado(id)
        if empleado_id.contract_id.calcula_indemnizacion:
            dias_laborados = self._get_dias_laborados(id)
            salario_promedio = self._get_salario_promedio(id)
            salario_diario = salario_promedio['salarios']['total_salario_promedio'] / 365
            regla_76_78 = ((salario_promedio['salarios']['total_salario_promedio'] /12) / 365) * dias_laborados
            regla_42_92 = ((salario_promedio['salarios']['total_salario_promedio'] /12) / 365) * dias_laborados
            indemnizacion = (salario_diario * dias_laborados) + regla_76_78 + regla_42_92
        return indemnizacion

    def empleados_inicio_anio(self,company_id,anio):
        empleados = 0
        empleado_ids = self.env['hr.employee'].search([['company_id', '=', company_id]])
        for empleado in empleado_ids:
            if empleado.contract_ids:
                for contrato in empleado.contract_ids:
                    if contrato.state == 'open':
                        anio_fin_contrato = 0
                        anio_inicio_contrato = int(datetime.strptime(str(contrato.date_start),'%Y-%m-%d').date().strftime('%Y'))
                        if contrato.date_end:
                            anio_fin_contrato = int(datetime.strptime(str(contrato.date_end),'%Y-%m-%d').date().strftime('%Y'))
                        if anio_inicio_contrato < anio and (contrato.date_end == False or anio_fin_contrato < anio) :
                            empleados += 1
        return empleados

    def empleados_fin_anio(self,company_id,anio):
        empleados = 0
        empleado_ids = self.env['hr.employee'].search([['company_id', '=', company_id]])
        for empleado in empleado_ids:
            if empleado.contract_ids:
                for contrato in empleado.contract_ids:
                    if contrato.state in ['open']:
                        anio_fin_contrato = 0
                        anio_inicio_contrato = int(datetime.strptime(str(contrato.date_start),'%Y-%m-%d').date().strftime('%Y'))
                        if contrato.date_end:
                            anio_fin_contrato = int(datetime.strptime(str(contrato.date_end),'%Y-%m-%d').date().strftime('%Y'))
                        if anio_inicio_contrato <= anio and (contrato.date_end == False or anio_fin_contrato <= anio) :
                            empleados += 1
        return empleados

    @api.multi
    def print_report(self):
        datas = {'ids': self.env.context.get('active_ids', [])}
        res = self.read(['anio'])
        res = res and res[0] or {}
        res['anio'] = res['anio']
        datas['form'] = res
        return self.env.ref('rrhh.action_informe_empleador').report_action([], data=datas)

    def dias_trabajados_anual(self,empleado_id,anio):
        anio_inicio_contrato = int(datetime.strptime(str(empleado_id.contract_id.date_start), '%Y-%m-%d').date().strftime('%Y'))
        anio_inicio = datetime.strptime(str(anio)+'-01'+'-01', '%Y-%m-%d').date().strftime('%Y-%m-%d')
        anio_fin = datetime.strptime(str(anio)+'-12'+'-31', '%Y-%m-%d').date().strftime('%Y-%m-%d')
        dias_laborados = 0
        if empleado_id.contract_id.date_start and empleado_id.contract_id.date_end:
            anio_fin_contrato = int(datetime.strptime(str(empleado_id.contract_id.date_end), '%Y-%m-%d').date().strftime('%Y'))
            if anio_inicio_contrato == anio and anio_fin_contrato == anio:
                dias = empleado_id.get_work_days_data(Datetime.from_string(empleado_id.contract_id.date_start), Datetime.from_string(empleado_id.contract_id.date_end), calendar=empleado_id.contract_id.resource_calendar_id)
                dias_laborados = dias['days']
            if anio_inicio_contrato != anio and anio_fin_contrato == anio:
                dias = empleado_id.get_work_days_data(Datetime.from_string(anio_inicio), Datetime.from_string(empleado_id.contract_id.date_end), calendar=empleado_id.contract_id.resource_calendar_id)
                dias_laborados = dias['days']
        if empleado_id.contract_id.date_start and empleado_id.contract_id.date_end == False:
            if anio_inicio_contrato == anio:
                dias = empleado_id.get_work_days_data(Datetime.from_string(empleado_id.contract_id.date_start), Datetime.from_string(anio_fin), calendar=empleado_id.contract_id.resource_calendar_id)
                dias_laborados = dias['days']
            else:
                dias = empleado_id.get_work_days_data(Datetime.from_string(anio_inicio), Datetime.from_string(anio_fin), calendar=empleado_id.contract_id.resource_calendar_id)
                dias_laborados = dias['days']
        return dias_laborados

    def print_report_excel(self):
        for w in self:
            dict = {}
            empleados_id = self.env.context.get('active_ids', [])
            libro = xlwt.Workbook()
            dict['anio'] = w['anio']
            empleados_archivados = self.env['hr.employee'].sudo().search([('active','=',False),('id', 'in', empleados_id)])
            empleados_activos = self.env['hr.employee'].sudo().search([('active','=',True),('id', 'in', empleados_id)])
            empleados = empleados_archivados + empleados_activos
            responsable_id = self.env['hr.employee'].sudo().search([['id', '=', self.env.user.id]])
            datos_compania = empleados[0].company_id

            # ESTILOS
            estilo_borde = xlwt.easyxf('border: bottom thin, left thin,right thin, top thin')
            xlwt.add_palette_colour("custom_colour", 0x21)
            libro.set_colour_RGB(0x21, 58, 137, 255)
            estilo = xlwt.easyxf('pattern: pattern solid, fore_colour custom_colour;border: bottom thin, left thin,right thin, top thin;align: wrap on, vert centre, horiz center')

            hoja_patrono = libro.add_sheet('Patrono')
            empleados_inicio_anio = self.empleados_inicio_anio(datos_compania.id,w['anio'])
            empleados_fin_anio = self.empleados_fin_anio(datos_compania.id,w['anio'])
            col_width = 100 * 75
            row_height = 35 * 30

            lista = [0]
            try:
                for i in lista:
                    hoja_patrono.col(i).width = col_width
                    hoja_patrono.row(i).height = row_height
            except ValueError:
                pass

            default_book_style = libro.default_style
            default_book_style.font.height = 20 * 36    # 36pt


            hoja_patrono.write(6,0,'Datos De Identificación',estilo_borde)
            hoja_patrono.write(7,0,'NIT',estilo_borde)
            hoja_patrono.write(7,1,datos_compania.vat,estilo_borde)
            hoja_patrono.write(8,0,'NOMBRE DE LA EMPRESA',estilo_borde)
            hoja_patrono.write(8,1,datos_compania.name,estilo_borde)
            hoja_patrono.write(9,0,'NACIONALIDAD DEL EMPLEADOR',estilo_borde)
            hoja_patrono.write(9,1,datos_compania.country_id.name,estilo_borde)
            hoja_patrono.write(10,0,'DENOMINACION O RAZON SOCIAL DEL PATRONO',estilo_borde)
            hoja_patrono.write(10,1,datos_compania.company_registry,estilo_borde)
            hoja_patrono.write(11,0,'NUMERO PATRONAL IGSS',estilo_borde)
            hoja_patrono.write(11,1,datos_compania.numero_patronal,estilo_borde)

            hoja_patrono.write(12,0,'Datos General',estilo_borde)
            hoja_patrono.write(13,0,'Barrio O Colonia',estilo_borde)
            hoja_patrono.write(13,1,datos_compania.barrio_colonia,estilo_borde)
            hoja_patrono.write(13,2,'Zona',estilo_borde)
            hoja_patrono.write(13,3,datos_compania.zona_centro_trabajo,estilo_borde)
            hoja_patrono.write(14,0,'Calle',estilo_borde)
            hoja_patrono.write(14,1,datos_compania.street2,estilo_borde)
            hoja_patrono.write(14,2,'Avenida',estilo_borde)
            hoja_patrono.write(14,3,datos_compania.street,estilo_borde)
            hoja_patrono.write(15,0,'Teléfono',estilo_borde)
            hoja_patrono.write(15,1,datos_compania.phone,estilo_borde)
            hoja_patrono.write(15,2,'Nomenclatura',estilo_borde)
            hoja_patrono.write(15,3,datos_compania.nomenclatura,estilo_borde)
            hoja_patrono.write(16,0,'Sitio Web',estilo_borde)
            hoja_patrono.write(16,1,datos_compania.website,estilo_borde)
            hoja_patrono.write(16,2,'E-Mail',estilo_borde)
            hoja_patrono.write(16,3,datos_compania.email,estilo_borde)
            hoja_patrono.write(17,0,'Existe Sindicato (SI) O (NO)',estilo_borde)
            hoja_patrono.write(17,1,datos_compania.sindicato,estilo_borde)

            hoja_patrono.write(19,0,'Ubicación Geográfica',estilo_borde)
            hoja_patrono.write(20,0,'País',estilo_borde)
            hoja_patrono.write(20,1,datos_compania.country_id.name,estilo_borde)
            hoja_patrono.write(20,2,'Región',estilo_borde)
            hoja_patrono.write(20,3,)
            hoja_patrono.write(21,0,'Departamento',estilo_borde)
            hoja_patrono.write(21,1,datos_compania.state_id.name,estilo_borde)
            hoja_patrono.write(21,2,'Municipio',estilo_borde)
            hoja_patrono.write(21,3,datos_compania.city,estilo_borde)
            hoja_patrono.write(22,0,'Datos Económicos',estilo_borde)
            hoja_patrono.write(23,0,'Año de Inicio de Operaciones',estilo_borde)
            hoja_patrono.write(23,1,datos_compania.anio_inicio_operaciones,estilo_borde)
            hoja_patrono.write(24,0,'Cantidad Total de Empleados Inicio de Año ',estilo_borde)
            hoja_patrono.write(24,1, empleados_inicio_anio,estilo_borde)
            hoja_patrono.write(25,0,'Cantidad Total de Empleados fin de Año',estilo_borde)
            hoja_patrono.write(25,1, empleados_fin_anio,estilo_borde)
            hoja_patrono.write(26,0,'Tamaño de la empresa por ventas anuales en salarios minimos',estilo_borde)
            hoja_patrono.write(26,1, datos_compania.tamanio_empresa_ventas,estilo_borde)
            hoja_patrono.write(27,0,'Tamaño de empresa según cantidad de Trabajadores',estilo_borde)
            hoja_patrono.write(27,1,datos_compania.tamanio_empresa_trabajadores,estilo_borde)
            hoja_patrono.write(28,0,'Tiene planificado contratar nuevo personal (SI) (NO)',estilo_borde)
            hoja_patrono.write(28,1,datos_compania.contratar_personal,estilo_borde)
            hoja_patrono.write(29,0,'Contabilidad Completa',estilo_borde)
            hoja_patrono.write(29,1,datos_compania.contabilidad_completa,estilo_borde)

            hoja_patrono.write(31,0,'Actividad Económica Principal',estilo_borde)
            hoja_patrono.write(32,0,'Actividad Gran Grupo',estilo_borde)
            hoja_patrono.write(32,1,datos_compania.actividad_gran_grupo,estilo_borde)
            hoja_patrono.write(33,0,'Actividad Económica',estilo_borde)
            hoja_patrono.write(33,1,datos_compania.actividad_economica,estilo_borde)
            hoja_patrono.write(34,0,'Sub Actividad Económica',estilo_borde)
            hoja_patrono.write(34,1,datos_compania.sub_actividad_economica,estilo_borde)
            hoja_patrono.write(35,0,'Ocupación Grupo',estilo_borde)
            hoja_patrono.write(35,1,datos_compania.ocupacion_grupo,estilo_borde)

            hoja_patrono.write(37,0,'Datos Del Contacto',estilo_borde)
            hoja_patrono.write(38,0,'Nombre Del Represéntate. Legal',estilo_borde)
            hoja_patrono.write(38,1,datos_compania.representante_legal_id.name,estilo_borde)
            hoja_patrono.write(39,0,'Tipo De Documento Del Represéntate. Legal ',estilo_borde)
            hoja_patrono.write(39,1,'DPI',estilo_borde)
            hoja_patrono.write(40,0,'Nombre Jefe De Recursos Humanos',estilo_borde)
            hoja_patrono.write(40,1,datos_compania.jefe_recursos_humanos_id.name,estilo_borde)
            hoja_patrono.write(41,0,'No. De Identificación De  Jefe De RR.HH.',estilo_borde)
            hoja_patrono.write(41,1,datos_compania.jefe_recursos_humanos_id.identification_id,estilo_borde)
            hoja_patrono.write(42,0,'E-Mail Del Jefe RR.HH.',estilo_borde)
            hoja_patrono.write(42,1,datos_compania.jefe_recursos_humanos_id.work_email,estilo_borde)
            hoja_patrono.write(43,0,'E-Mail Del Responsable Del Informe ',estilo_borde)
            hoja_patrono.write(43,1,responsable_id.work_email,estilo_borde)
            hoja_patrono.write(44,0,'Teléfono Del Represéntate Del Informe',estilo_borde)
            hoja_patrono.write(44,1,responsable_id.work_phone,estilo_borde)
            hoja_patrono.write(45,0,'Nacionalidad Del Representante Legal',estilo_borde)
            hoja_patrono.write(45,1, datos_compania.representante_legal_id.country_id.name,estilo_borde)
            hoja_patrono.write(46,0,'No. De Identificación Del Represéntate Legal',estilo_borde)
            hoja_patrono.write(46,1, datos_compania.representante_legal_id.identification_id,estilo_borde)
            hoja_patrono.write(47,0,'Tipo De Documentación Del Jefe De RR.HH.',estilo_borde)
            hoja_patrono.write(47,1, 'DPI',estilo_borde)
            hoja_patrono.write(48,0,'Teléfono Jefe RR.HH.',estilo_borde)
            hoja_patrono.write(48,1, datos_compania.jefe_recursos_humanos_id.work_phone,estilo_borde)
            hoja_patrono.write(49,0,'Nombre Del Represéntate de Elaborar el Informe Del Empleador',estilo_borde)
            hoja_patrono.write(49,1, responsable_id.name,estilo_borde)
            hoja_patrono.write(50,0,'Documento Identificación Responsable',estilo_borde)
            hoja_patrono.write(50,1, responsable_id.identification_id,estilo_borde)
            hoja_patrono.write(51,0,'Nacionalidad Del Responsable',estilo_borde)
            hoja_patrono.write(51,1, responsable_id.country_id.name,estilo_borde)
            hoja_patrono.write(52,0,'Año Del Informe ',estilo_borde)
            hoja_patrono.write(52,1,dict['anio'],estilo_borde)

            hoja_empleado = libro.add_sheet('Empleado')
            datos = libro.add_sheet('Hoja2')
            xlwt.add_palette_colour("custom_colour_pink", 0x24)
            libro.set_colour_RGB(0x24, 228, 55, 247)
            # estilo_rosado = xlwt.easyxf('pattern: pattern solid, fore_colour custom_colour_purp;border: bottom thin, left thin,right thin, top thin;align: wrap on, vert centre, horiz center')

            lista = [0]
            try:
                for i in lista:
                    hoja_empleado.col(i).width = col_width
                    hoja_empleado.row(i).height = row_height
            except ValueError:
                pass

            hoja_empleado.write(0, 0, 'Numero de trabajadores')
            hoja_empleado.write(0, 1, 'Primer Nombre')
            hoja_empleado.write(0, 2, 'Segundo Nombre')
            hoja_empleado.write(0, 3, 'Primer Apellido')
            hoja_empleado.write(0, 4, 'Segundo Apellido')
            hoja_empleado.write(0, 5, 'Nacionalidad')
            hoja_empleado.write(0, 6, 'Estado Civil')
            hoja_empleado.write(0, 7, 'Documento Identificación')
            hoja_empleado.write(0, 8, 'Número de Documento')
            hoja_empleado.write(0, 9, 'Pais Origen')
            hoja_empleado.write(0, 10, 'Lugar Nacimiento')
            hoja_empleado.write(0, 11, 'Número de Identificación Tributaria NIT')
            hoja_empleado.write(0, 12, 'Número de Afiliación IGSS')
            hoja_empleado.write(0, 13, 'Sexo (M) O (F)')
            hoja_empleado.write(0, 14, 'Fecha Nacimiento')
            hoja_empleado.write(0, 15, 'Cantidad de Hijos')
            hoja_empleado.write(0, 16, 'A trabajado en el extranjero ')
            hoja_empleado.write(0, 17, 'Ocupación en el extranjero')
            hoja_empleado.write(0, 18, 'Pais')
            hoja_empleado.write(0, 19, 'Motivo de finalización de la relación laboral en el extranjero')
            hoja_empleado.write(0, 20, 'Nivel Academico')
            hoja_empleado.write(0, 21, 'Título o diploma obtenido')
            hoja_empleado.write(0, 22, 'Pueblo de pertenencia')
            hoja_empleado.write(0, 23, 'Idiomas que dominca')

            xlwt.add_palette_colour("custom_colour_azul", 0x25)
            libro.set_colour_RGB(0x25, 55, 81, 247)
            estilo_azul = xlwt.easyxf('pattern: pattern solid, fore_colour custom_colour_azul;border: bottom thin, left thin,right thin, top thin')
            hoja_empleado.write(0, 24, 'Temporalidad del contrato')
            hoja_empleado.write(0, 25, 'Tipo Contrato')
            hoja_empleado.write(0, 26, 'Fecha Inicio Labores')
            hoja_empleado.write(0, 27, 'Fecha Reinicio-laboreso')
            hoja_empleado.write(0, 28, 'Fecha Retiro Labores')
            hoja_empleado.write(0, 29, 'Ocupación')
            hoja_empleado.write(0, 30, 'Jornada de Trabajo')
            hoja_empleado.write(0, 31, 'Dias Laborados en el Año')



            xlwt.add_palette_colour("custom_colour_amarillo", 0x26)
            libro.set_colour_RGB(0x26, 239, 255, 0)
            estilo_amarillo = xlwt.easyxf('pattern: pattern solid, fore_colour custom_colour_amarillo;border: bottom thin, left thin,right thin, top thin;align: wrap on, vert centre, horiz center')
            hoja_empleado.write(0, 32, 'Número de expediente del permiso de extranjero')
            hoja_empleado.write(0, 33, 'Salario Mensual Nominal')
            hoja_empleado.write(0, 34, 'Salario Anual Nominal')
            hoja_empleado.write(0, 35, 'Bonificación Decreto 78-89  (Q.250.00)')
            #Total Horas Extras Anuales Numero de horas (en cantidad 1, 2 o 3 horas)
            hoja_empleado.write(0, 36, 'Total Horas Extras Anuales')
            #Valor de Hora Extra sumas todas las horas en Q y dividir dentrode horas extras anuales (numero de horas)
            hoja_empleado.write(0, 37, 'Valor de Hora Extra')
            hoja_empleado.write(0, 38, 'Monto Aguinaldo Decreto 76-78')
            hoja_empleado.write(0, 39, 'Monto Bono 14  Decreto 42-92')
            hoja_empleado.write(0, 40, 'Retribución por Comisiones')
            hoja_empleado.write(0, 41, 'Viaticos')
            hoja_empleado.write(0, 42, 'Bonificaciones Adicionales')
            hoja_empleado.write(0, 43, 'Retribución por vacaciones')
            hoja_empleado.write(0, 44, 'Retribución por Indemnización (Articulo 82)')
            # hoja_empleado.write(0, 45, 'Nombre, Denominación  o Razón Social del Patrono')

            fila = 1
            empleado_numero = 1
            numero = 1
            for empleado in empleados:
                logging.warn(empleado)
                nombre_empleado = empleado.name.split( )
                if empleado.primer_nombre:
                    nominas_lista = []
                    contrato = self.env['hr.contract'].search([('employee_id', '=', empleado.id),('state','=',['open','pending','close']  )])
                    nomina_id = self.env['hr.payslip'].search([['employee_id', '=', empleado.id]])
                    dias_trabajados = 0
                    salario_anual_nominal = 0
                    bonificacion = 0
                    estado_civil = 0
                    horas_extras = 0
                    aguinaldo = 0
                    bono = 0
                    bonificaciones_adicionales = 0
                    numero_horas_extra = 0
                    retribucion_comisiones = 0
                    viaticos = 0
                    retribucion_vacaciones = 0
                    bonificacion_decreto = 0
                    numero_nominas_bono = 0
                    salario_anual_nominal_promedio = 0
                    numero_nominas_salario = 0
                    precision_currency = empleado.company_id.currency_id
                    indemnizacion = precision_currency.round(self._get_indemnizacion(empleado.id)) if empleado.contract_ids[0].date_end else 0
                    nominas = {}
                    for nomina in nomina_id:
                        nomina_anio = datetime.strptime(str(nomina.date_from), "%Y-%m-%d").year
                        nomina_mes = datetime.strptime(str(nomina.date_from), "%Y-%m-%d").month
                        if w['anio'] == nomina_anio:
                            if nomina.input_line_ids:
                                for entrada in nomina.input_line_ids:
                                    for horas_entrada in nomina.company_id.numero_horas_extras_ids:
                                        if entrada.code == horas_entrada.code:
                                            numero_horas_extra += entrada.amount
                            for linea in nomina.worked_days_line_ids:
                                dias_trabajados += linea.number_of_days
                            for linea in nomina.line_ids:
                                if linea.salary_rule_id.id in nomina.company_id.salario_ids.ids:
                                    salario_anual_nominal += linea.total
                                    if nomina_mes not in nominas:
                                        nominas[nomina_mes] = {'salario': 0,'bonificacion':0}
                                    nominas[nomina_mes]['salario'] += salario_anual_nominal
                                    numero_nominas_salario += 1
                                if linea.salary_rule_id.id in nomina.company_id.bonificacion_ids.ids:
                                    bonificacion += linea.total
                                if linea.salary_rule_id.id in nomina.company_id.aguinaldo_ids.ids:
                                    aguinaldo += linea.total
                                if linea.salary_rule_id.id in nomina.company_id.bono_ids.ids:
                                    bono += linea.total
                                if linea.salary_rule_id.id in nomina.company_id.horas_extras_ids.ids:
                                    horas_extras += linea.total
                                if linea.salary_rule_id.id in nomina.company_id.retribucion_comisiones_ids.ids:
                                    retribucion_comisiones += linea.total
                                if linea.salary_rule_id.id in nomina.company_id.viaticos_ids.ids:
                                    viaticos += linea.total
                                if linea.salary_rule_id.id in nomina.company_id.retribucion_vacaciones_ids.ids:
                                    retribucion_vacaciones += linea.total
                                if linea.salary_rule_id.id in nomina.company_id.bonificaciones_adicionales_ids.ids:
                                    bonificaciones_adicionales += linea.total
                                if linea.salary_rule_id.id in nomina.company_id.decreto_ids.ids:
                                    bonificacion_decreto += linea.total
                                    if nomina_mes not in nominas:
                                        nominas[nomina_mes] = {'salario': 0,'bonificacion':0}
                                    nominas[nomina_mes]['bonificacion'] += bonificacion_decreto
                                    numero_nominas_bono += 1
                    bonificacion_decreto = bonificacion_decreto / len(nominas) if bonificacion_decreto > 0 else 0
                    salario_anual_nominal_promedio = salario_anual_nominal / len(nominas) if salario_anual_nominal > 0 else 0
                    if empleado.gender == 'male':
                        genero = 'H'
                    if empleado.gender == 'female':
                        genero = 'M'
                    if empleado.marital == 'single':
                        estado_civil = 1
                    if empleado.marital == 'married':
                        estado_civil = 2
                    if empleado.marital == 'widower':
                        estado_civil = 3
                    if empleado.marital == 'divorced':
                        estado_civil = 4
                    if empleado.marital == 'separado':
                        estado_civil = 5
                    if empleado.marital == 'unido':
                        estado_civil = 6
                    dias_trabajados_anual = self.dias_trabajados_anual(empleado,w['anio'])
                    hoja_empleado.write(fila, 0, empleado_numero,estilo_borde)
                    hoja_empleado.write(fila, 1, empleado.primer_nombre if empleado.primer_nombre else '',estilo_borde)
                    hoja_empleado.write(fila, 2, empleado.segundo_nombre if empleado.segundo_nombre else '',estilo_borde)
                    hoja_empleado.write(fila, 3, empleado.primer_apellido if empleado.primer_apellido else '',estilo_borde)
                    hoja_empleado.write(fila, 4, empleado.segundo_apellido if empleado.segundo_apellido else '',estilo_borde)
                    hoja_empleado.write(fila, 5, empleado.country_id.name,estilo_borde)
                    hoja_empleado.write(fila, 6, estado_civil,estilo_borde)
                    hoja_empleado.write(fila, 7, empleado.documento_identificacion,estilo_borde)
                    hoja_empleado.write(fila, 8, empleado.identification_id,estilo_borde)
                    hoja_empleado.write(fila, 9, empleado.pais_origen.name,estilo_borde)
                    hoja_empleado.write(fila, 10, empleado.place_of_birth,estilo_borde)
                    hoja_empleado.write(fila, 11, empleado.nit,estilo_borde)
                    hoja_empleado.write(fila, 12, empleado.igss,estilo_borde)
                    hoja_empleado.write(fila, 13, genero,estilo_borde)
                    hoja_empleado.write(fila, 14, empleado.birthday,estilo_borde)
                    hoja_empleado.write(fila, 15, empleado.children,estilo_borde)
                    hoja_empleado.write(fila, 16, empleado.trabajado_extranjero,estilo_borde)
                    hoja_empleado.write(fila, 17, empleado.forma_trabajo_extranjero,estilo_borde)
                    hoja_empleado.write(fila, 18, empleado.pais_trabajo_extranjero_id.name,estilo_borde)
                    hoja_empleado.write(fila, 19, empleado.finalizacion_laboral_extranjero,estilo_borde)
                    hoja_empleado.write(fila, 20, empleado.nivel_academico,estilo_borde)
                    hoja_empleado.write(fila, 21, empleado.profesion,estilo_borde)
                    hoja_empleado.write(fila, 22, empleado.pueblo_pertenencia,estilo_borde)
                    hoja_empleado.write(fila, 23, empleado.idioma,estilo_borde)
                    hoja_empleado.write(fila, 24, contrato.temporalidad_contrato,estilo_borde)
                    hoja_empleado.write(fila, 25, contrato.type_id.name,estilo_borde)
                    hoja_empleado.write(fila, 26, contrato.date_start,estilo_borde)
                    hoja_empleado.write(fila, 27, contrato.fecha_reinicio_labores,estilo_borde)
                    hoja_empleado.write(fila, 28, contrato.date_end,estilo_borde)
                    hoja_empleado.write(fila, 29, contrato.job_id.name,estilo_borde)
                    hoja_empleado.write(fila, 30, empleado.jornada_trabajo,estilo_borde)
                    hoja_empleado.write(fila, 31, dias_trabajados_anual,estilo_borde)
                    hoja_empleado.write(fila, 32, empleado.permiso_trabajo,estilo_borde)
                    hoja_empleado.write(fila, 33, salario_anual_nominal_promedio,estilo_borde)
                    hoja_empleado.write(fila, 34, salario_anual_nominal,estilo_borde)
                    # hoja_empleado.write(fila, 34, (contrato.wage + contrato.base_extra) * 12,estilo_borde)
                    hoja_empleado.write(fila, 35, bonificacion_decreto,estilo_borde)
                    hoja_empleado.write(fila, 36, numero_horas_extra,estilo_borde)

                    # hoja_empleado.write(fila, 36, horas_extras,estilo_borde)
                    # hoja_empleado.write(fila, 37, ((horas_extras / numero_horas_extra) if numero_horas_extra > 0 else horas_extras),estilo_borde)
                    hoja_empleado.write(fila, 37, horas_extras/numero_horas_extra if numero_horas_extra > 0 else 0,estilo_borde)
                    hoja_empleado.write(fila, 38, aguinaldo,estilo_borde)
                    hoja_empleado.write(fila, 39, bono,estilo_borde)
                    hoja_empleado.write(fila, 40, retribucion_comisiones,estilo_borde)
                    hoja_empleado.write(fila, 41, viaticos,estilo_borde)
                    hoja_empleado.write(fila, 42, bonificaciones_adicionales,estilo_borde)
                    hoja_empleado.write(fila, 43, retribucion_vacaciones,estilo_borde)
                    hoja_empleado.write(fila, 44, indemnizacion,estilo_borde)
                    # hoja_empleado.write(fila, 45, datos_compania.company_registry,estilo_borde)
                    empleado_numero +=1

                    fila += 1
                    numero += 1

            f = io.BytesIO()
            libro.save(f)
            datos = base64.b64encode(f.getvalue())
            self.write({'archivo':datos, 'name':'informe_del_empleador.xls'})

        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'rrhh.informe_empleador',
            'res_id': self.id,
            'view_id': False,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }
