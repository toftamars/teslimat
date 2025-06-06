from odoo import api, fields, models, _
from odoo.exceptions import UserError

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    # Teslimat belgeleri ilişkisi
    delivery_document_count = fields.Integer('Teslimat Belgesi Sayısı', 
                                          compute='_compute_delivery_document_count')
    delivery_document_ids = fields.One2many('delivery.document', 'picking_id', 
                                          string='Teslimat Belgeleri')
    is_delivery_created = fields.Boolean('Teslimat Oluşturuldu', compute='_compute_is_delivery_created',
                                       store=True)
    
    # Teslimat için uygunluk
    is_delivery_ready = fields.Boolean('Teslimat İçin Hazır', 
                                      compute='_compute_delivery_ready')
    has_vehicle_selected = fields.Boolean('Araç Seçildi', default=False)
    
    @api.depends('delivery_document_ids')
    def _compute_delivery_document_count(self):
        for record in self:
            record.delivery_document_count = len(record.delivery_document_ids)
    
    @api.depends('delivery_document_ids')
    def _compute_is_delivery_created(self):
        for record in self:
            record.is_delivery_created = bool(record.delivery_document_ids)
    
    @api.depends('state', 'has_vehicle_selected')
    def _compute_delivery_ready(self):
        for record in self:
            record.is_delivery_ready = (
                record.state == 'done' and 
                record.has_vehicle_selected and
                record.picking_type_code == 'outgoing'
            )
    
    def action_view_delivery_documents(self):
        """Teslimat belgelerini görüntüle"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Teslimat Belgeleri'),
            'view_mode': 'tree,form',
            'res_model': 'delivery.document',
            'domain': [('picking_id', '=', self.id)],
            'context': {'create': False},
        }
    
    def action_create_delivery_document(self):
        """Teslimat belgesi oluştur"""
        self.ensure_one()
        
        # Teslimat belgesi zaten oluşturulmuş mu kontrol et
        if self.is_delivery_created:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Teslimat Belgeleri'),
                'view_mode': 'tree,form',
                'res_model': 'delivery.document',
                'domain': [('picking_id', '=', self.id)],
                'context': {'create': False},
            }
        
        # Yeni teslimat belgesi oluştur
        delivery_document = self.env['delivery.document'].create({
            'picking_id': self.id,
            'delivery_date': fields.Date.context_today(self),
        })
        
        # Oluşturulan teslimat belgesini aç
        return {
            'type': 'ir.actions.act_window',
            'name': _('Teslimat Belgesi'),
            'view_mode': 'form',
            'res_model': 'delivery.document',
            'res_id': delivery_document.id,
            'target': 'current',
        }
    
    def action_select_vehicle(self):
        """Araç seçimi wizard'ını aç"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Araç Seçimi'),
            'view_mode': 'form',
            'res_model': 'vehicle.selection.wizard',
            'target': 'new',
            'context': {'default_picking_id': self.id},
        }