# -*- encoding: utf-8 -*-

from odoo import api, models, fields
import logging

class ReportRecibo(models.AbstractModel):
    _name = 'report.rrhh.recibo'

    def lineas(self, o):
        result = {'lineas': [], 'totales': [0, 0]}
        if o.employee_id.recibo_id:

            lineas_reglas = {}
            for l in o.line_ids:
                if l.salary_rule_id.id not in lineas_reglas:
                    lineas_reglas[l.salary_rule_id.id] = 0
                lineas_reglas[l.salary_rule_id.id] += l.total

            recibo = o.employee_id.recibo_id
            lineas_ingresos = []
            for li in recibo.linea_ingreso_id:
                datos = {'nombre': li.name, 'total': 0}
                for r in li.regla_id:
                    datos['total'] += lineas_reglas.get(r.id, 0)
                    result['totales'][0] += lineas_reglas.get(r.id, 0)
                lineas_ingresos.append(datos)

            lineas_deducciones = []
            for ld in recibo.linea_deduccion_id:
                datos = {'nombre': ld.name, 'total': 0}
                for r in ld.regla_id:
                    datos['total'] += lineas_reglas.get(r.id, 0)
                    result['totales'][1] += lineas_reglas.get(r.id, 0)
                lineas_deducciones.append(datos)

            largo = max(len(lineas_ingresos), len(lineas_deducciones))
            lineas_ingresos += [None] * (largo - len(lineas_ingresos))
            lineas_deducciones += [None] * (largo - len(lineas_deducciones))

            result['lineas'] = zip(lineas_ingresos, lineas_deducciones)

        return result

    @api.model
    def render_html(self, docids, data=None):
        self.model = 'hr.payslip'
        docs = self.env[self.model].browse(docids)

        docargs = {
            'doc_ids': docids,
            'doc_model': self.model,
            'docs': docs,
            'lineas': self.lineas,
        }
        return self.env['report'].render('rrhh.recibo', docargs)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: