# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import googlemaps
import json
from datetime import datetime, timedelta

class DeliveryRoute(models.Model):
    _name = 'delivery.route'
    _description = 'Teslimat Rotası'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char('Rota No', required=True, copy=False, readonly=True,
                      default=lambda self: _('Yeni'))
    planning_id = fields.Many2one('delivery.planning', string='Teslimat Planlaması',
                                 required=True, tracking=True)
    vehicle_type = fields.Selection(related='planning_id.vehicle_type', store=True)
    
    # Rota Detayları
    start_location = fields.Char('Başlangıç Noktası', required=True, tracking=True)
    end_location = fields.Char('Bitiş Noktası', required=True, tracking=True)
    waypoints = fields.Text('Ara Noktalar', tracking=True)
    
    # Optimizasyon Sonuçları
    total_distance = fields.Float('Toplam Mesafe (km)', tracking=True)
    total_duration = fields.Float('Toplam Süre (dk)', tracking=True)
    optimized_route = fields.Text('Optimize Edilmiş Rota', tracking=True)
    
    # Durum
    state = fields.Selection([
        ('draft', 'Taslak'),
        ('optimized', 'Optimize Edildi'),
        ('in_progress', 'Devam Ediyor'),
        ('done', 'Tamamlandı')
    ], string='Durum', default='draft', tracking=True)
    
    # Google Maps API
    api_key = fields.Char('Google Maps API Key', 
                         default=lambda self: self.env['ir.config_parameter'].sudo().get_param('delivery.google_maps_api_key'))
    
    @api.model
    def create(self, vals):
        if vals.get('name', _('Yeni')) == _('Yeni'):
            vals['name'] = self.env['ir.sequence'].next_by_code('delivery.route') or _('Yeni')
        return super().create(vals)

    def action_optimize_route(self):
        """Rotayı optimize et"""
        self.ensure_one()
        
        if not self.api_key:
            raise ValidationError(_('Google Maps API anahtarı tanımlanmamış!'))
        
        try:
            # Google Maps istemcisini oluştur
            gmaps = googlemaps.Client(key=self.api_key)
            
            # Teslimat noktalarını al
            delivery_points = self.planning_id.delivery_ids.mapped('delivery_address')
            
            # Rota optimizasyonu için istek
            result = gmaps.directions(
                origin=self.start_location,
                destination=self.end_location,
                waypoints=delivery_points,
                optimize_waypoints=True,
                mode="driving"
            )
            
            if not result:
                raise ValidationError(_('Rota hesaplanamadı!'))
            
            # Sonuçları kaydet
            route = result[0]
            legs = route['legs']
            
            # Toplam mesafe ve süre
            total_distance = sum(leg['distance']['value'] for leg in legs) / 1000  # km'ye çevir
            total_duration = sum(leg['duration']['value'] for leg in legs) / 60  # dakikaya çevir
            
            # Optimize edilmiş sıralama
            optimized_order = []
            for i, leg in enumerate(legs):
                if i < len(delivery_points):
                    optimized_order.append({
                        'address': delivery_points[i],
                        'distance': leg['distance']['text'],
                        'duration': leg['duration']['text']
                    })
            
            # Sonuçları güncelle
            self.write({
                'total_distance': total_distance,
                'total_duration': total_duration,
                'optimized_route': json.dumps(optimized_order, indent=2),
                'state': 'optimized'
            })
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Başarılı'),
                    'message': _('Rota başarıyla optimize edildi.'),
                    'sticky': False,
                    'type': 'success'
                }
            }
            
        except Exception as e:
            raise ValidationError(_('Rota optimizasyonu sırasında hata oluştu: %s') % str(e))

    def action_start_route(self):
        """Rotayı başlat"""
        self.ensure_one()
        if self.state != 'optimized':
            raise ValidationError(_('Sadece optimize edilmiş rotalar başlatılabilir!'))
        self.state = 'in_progress'

    def action_complete_route(self):
        """Rotayı tamamla"""
        self.ensure_one()
        if self.state != 'in_progress':
            raise ValidationError(_('Sadece devam eden rotalar tamamlanabilir!'))
        self.state = 'done'

    def action_reset_to_draft(self):
        """Taslağa dönüştür"""
        self.ensure_one()
        self.state = 'draft'
        self.total_distance = 0
        self.total_duration = 0
        self.optimized_route = False

    def get_route_map_url(self):
        """Google Maps URL'sini oluştur"""
        self.ensure_one()
        if not self.optimized_route:
            return False
            
        # Optimize edilmiş rotayı al
        route_points = json.loads(self.optimized_route)
        
        # URL parametrelerini oluştur
        params = {
            'origin': self.start_location,
            'destination': self.end_location,
            'waypoints': '|'.join(point['address'] for point in route_points),
            'travelmode': 'driving'
        }
        
        # URL'yi oluştur
        base_url = 'https://www.google.com/maps/dir/'
        query_string = '&'.join(f'{k}={v}' for k, v in params.items())
        
        return f"{base_url}?{query_string}" 