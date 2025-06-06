# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError

class VehicleSelectionWizard(models.TransientModel):
    _name = 'vehicle.selection.wizard'
    _description = 'Araç Seçimi Wizard'

    picking_id = fields.Many2one('stock.picking', string='Transfer Belgesi', required=True)
    
    vehicle_type = fields.Selection([
        ('anadolu', 'Anadolu Yakası'),
        ('avrupa', 'Avrupa Yakası'),
        ('kucuk_arac_1', 'Küçük Araç 1'),
        ('kucuk_arac_2', 'Küçük Araç 2'),
        ('ek_arac', 'Ek Araç')
    ], string='Araç Seçimi', required=True)
    
    def action_confirm(self):
        """Araç seçimini onayla"""
        self.ensure_one()
        
        if not self.vehicle_type:
            raise UserError(_('Araç seçimi yapılmalıdır!'))
        
        # Transfer belgesine araç seçimi bilgisini ekle
        self.picking_id.write({
            'has_vehicle_selected': True,
        })
        
        # Teslimat belgesi oluştur
        return self.picking_id.action_create_delivery_document()