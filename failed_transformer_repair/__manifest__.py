{
    'name': 'Failed transformer Repair',
    'summary': 'This tracks the movement of failed transformer',
    'description': 'This module is about failed transformer',
    'version': '0.1',
    'depends': [
        'base','hr','mail'
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/failed_transformer_movement_views.xml',
        'views/tranformer_views.xml',
        'views/menus.xml'
    ],
}