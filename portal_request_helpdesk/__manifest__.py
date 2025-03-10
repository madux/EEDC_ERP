{
    'name': 'Portal Request helpdesk',
    'version': '16.0.1',
    'author': "Maduka Sopulu",
    'category': 'Portal request',
    'summary': 'Enable helpdesk for external users ',
    'depends': ['base', 'website', 'portal_request', 'helpdesk', 'ik_multi_branch'],
    'description': "Added features of users to request for helpdesk on portal request",
    "data": [
        'static/templates/menu.xml',
        'static/templates/helpdesk_form.xml',
        'views/helpdesk.xml',
    ],
    # 'qweb': [
    #     'static/xml/partials.xml',
    # ],
    'assets': {
        'web.assets_frontend': [
        '/portal_request_helpdesk/static/src/js/helpdesk_form.js',
    ]},
}
