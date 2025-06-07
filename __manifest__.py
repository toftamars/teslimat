{
    'name': 'teslimat',
    'version': '15.0.1.0.0',
    'category': 'Inventory/Delivery',
    'summary': 'Transfer belgelerinden otomatik teslimat belgesi oluşturma ve yönetimi',
    'description': """
Teslimat Yönetimi Modülü
========================
* Transfer belgelerinden otomatik teslimat belgesi oluşturma
* İlçe bazlı teslimat günleri planlaması
* SMS entegrasyonu ile müşteri bilgilendirme
* Araç ve rota yönetimi
* Günlük teslimat limiti kontrolü
* Rota optimizasyonu ve harita entegrasyonu
* Detaylı raporlama ve analiz
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'base',
        'web',
        'mail',
        'stock',
        'contacts',
        'sms',
        'fleet',
        'report',
    ],
    'data': [
        'security/delivery_security.xml',
        'security/ir.model.access.csv',
        'views/delivery_document_views.xml',
        'views/delivery_planning_views.xml',
        'views/delivery_route_views.xml',
        'views/delivery_report_views.xml',
        'views/stock_picking_views.xml',
        'views/delivery_menus.xml',
        'wizard/vehicle_selection_wizard_views.xml',
        'data/delivery_data.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
    'external_dependencies': {
        'python': ['googlemaps'],
    },
    'assets': {
        'web.assets_backend': [
            'static/src/js/*.js',
            'static/src/css/*.css',
        ],
    },
    'images': ['static/description/banner.png'],
    'icon': 'static/description/icon.png',
    'sequence': 2,
}