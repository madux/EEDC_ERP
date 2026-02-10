from odoo import http
from odoo.http import request
import json
import logging
# from odoo.addons.eha_auth.controllers.helpers import validate_token, validate_secret_key, invalid_response, valid_response
import werkzeug.wrappers
from odoo import fields
from odoo.exceptions import ValidationError
import functools
from datetime import datetime,date,timedelta

def invalid_response(typ, message=None, status=401):
    """Invalid Response
    This will be the return value whenever the server runs into an error
    either from the client or the server."""
    # return json.dumps({})
    return werkzeug.wrappers.Response(
    status=status,
    content_type="application/json; charset=utf-8",
    response=json.dumps(
        {
            "type": typ,
            "message": str(message)
            if str(message)
            else "wrong arguments (missing validation)",
        },
        default=datetime.isoformat,
    ),
)

logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger(__name__)

class APIControllers(http.Controller):

    # logging.basicConfig(level=logging.INFO)
    # _logger = logging.getLogger(__name__)
    # class EmailAPI(http.Controller):
    def validate_token(func):
        """."""

        @functools.wraps(func)
        def wrap(self, *args, **kwargs):
            """."""
            token = request.httprequest.headers.get("token")
            if not token:
                return invalid_response(
                    "token_not_found", "please provide token in the request header", 401
                )
            access_token_data = (
                request.env["user.api.token"]
                .sudo()
                .search([("token", "=", token)], order="id DESC", limit=1)
            )
            _logger.info(f"ASCCES DATA {access_token_data} AND {token}")
            if (access_token_data.find_one_or_create_token(user_id=access_token_data.user_id.id) != token):
                return invalid_response(
                    "token", "Invalid Token", 401
                )

            request.session.uid = access_token_data.user_id.id
            
            request.session.session_token = token
            request.update_env(
                user=access_token_data.user_id.id,
                context=dict(request.env.context),
                su=False
            )
            # request.update_env(user=access_token_data.user_id.id, context=None, su=None)
            return func(self, *args, **kwargs)
        return wrap
    
    @http.route('/api/send_email', type='json', auth='public', methods=['POST'], csrf=False)
    def send_email(self, **kwargs):
        try:
            data = json.loads(request.httprequest.data)
            recipient_email = data.get('recipient_email')
            subject = data.get('subject')
            body = data.get('body')
            if not all([recipient_email, subject, body]):
                return {'success': False, 'message': 'Missing required fields'}
            mail_values = {
                'email_to': recipient_email,
                'subject': subject,
                'body_html': body,
                'auto_delete': True,
            }
            mail = request.env['mail.mail'].sudo().create(mail_values)
            mail.send()
            return {'success': True, 'message': 'Email sent successfully'}
        except Exception as e:
            return {'success': False, 'message': str(e)}
       
     
    @validate_token
    @http.route(['/api/eedc/get-district'], type="http", methods=["GET"], website=True, csrf=False, auth="none")
    def get_eedc_district(self, **kwargs):
        '''
        {'params': {
                'district_id': 1 or null
                'name': 'Awka' or null
            }
        }
        if  id, returns the specific district by id else returns all district
        '''
        try: 
            # req_data = json.loads(request.httprequest.data) # kwargs 
            data = request.params
            district_id = int(data.get('district_id')) if data.get('district_id') else False 
            _logger.info(f"KWARGS {kwargs} DATA {data} VALUE OF district_id IS {data.get('district_id')} and type {type(data)} {data.keys()}")
            domain = [('id', '=', district_id)] if district_id else []
            districts = request.env['feeder.district'].sudo().search(domain)
            if districts:
                data = []
                for prd in districts:
                    data.append({
                        'id': prd.id, 'name': prd.name, 
                    })
                return json.dumps({
                    'success': True, 
                    'data':data
                    })
            else:
                return json.dumps({
                    'success': False, 
                    'message': 'No district found'})  
        
        except Exception as e:
            return json.dumps({
                    'success': False, 
                    'message': str(e)})
    

    def data_validations(self, kwargs):
        create_date = False 
        staff_number = False
        employee_id = False
        end_date = False
        # company_id = False
        if kwargs.get('staff_number'):
            staff_number = str(kwargs.get('staff_number'))
        if kwargs.get('create_date'):
            try:
                c_date = str(kwargs.get('create_date'))
                create_date = datetime.strptime(c_date, '%d/%m/%Y')
            except Exception as err:
                return {
                    'status': False, 
                    'message': f"The Endpoint encountered error. Wrong date format ==>: {err}",
                    'data': {}
                }
                
        if kwargs.get('end_date'):
            try:
                c_date = str(kwargs.get('end_date'))
                end_date = datetime.strptime(c_date, '%d/%m/%Y')
            except Exception as err:
                return {
                    'status': False, 
                    'message': f"The Endpoint encountered error. Wrong end date format ==>: {err}",
                    'data': {}
                }
        if kwargs.get('id'):
            employee_id = int(kwargs.get('id'))
         
        
        return staff_number, create_date, employee_id, end_date
    
    @validate_token
    @http.route(['/api/employee-info'], type='http', methods=['GET'], auth='none', csrf=False)
    def EmployeeData(self, **kwargs):
        expected_param = '''
        {'params': {
                'create_date': 12/12/2023,
                'staff_number': '23450' or null,
                'id': 560
            }
        }'''
        employee_details = [] # e.g [{'name': 'Maduka Sopulu', 'phone': 0292900}, {}, {}, {}.........{}]
        data = request.params
        staff_number, create_date, employee_id, end_date = self.data_validations(data)
        domain = [('active', '=', True)] # gives you all records
        if staff_number:
            domain = domain + [
                ('employee_number', '=ilike', staff_number)
            ]
        if create_date:
            domain = domain + [
                ('create_date', '>=', create_date),
            ]
        if employee_id:
            domain = domain + [
                ('id', '=', employee_id),
            ]
        _logger.info(f"What is domain {domain} == params == {data} ====={kwargs} ====")
        employees = request.env['hr.employee'].sudo().search(domain, limit=10)
        if employees:
            for emp in employees:
                responseData = {
                    'id': emp.id,
                    'company_id': emp.company_id.id,
                    'company_name': emp.company_id.name,
                    'full_name': emp.name,
                    'work_email': emp.work_email,
                    'staff_number': emp.employee_number,
                    'job_position_id': emp.job_id.id,
                    'job_position_name': emp.job_id.name,
                    'employee_date': datetime.strftime(emp.first_contract_date, '%d/%m/%Y') if emp.first_contract_date else False,
                    'erp_create_date': datetime.strftime(emp.create_date, '%d/%m/%Y') if emp.create_date else False,
                    'first_name': emp.first_name,
                    'middle_name': emp.middle_name,
                    'department_id': emp.department_id.id,
                    'department_name': emp.department_id.name,
                    'district_id': emp.branch_id.id,
                    'district_name': emp.branch_id.name,
                    'manager_id': emp.parent_id.id,
                    'manager_name': emp.parent_id.name,
                    'supervisor_id': emp.administrative_supervisor_id.id,
                    'supervisor_name': emp.administrative_supervisor_id.name,
                    'is_contract_staff': True if emp.is_external_staff else False, 
                    # 'image': emp.image_1920,
                    # 'image': base64.b64encode(emp.image_1920).decode('utf-8') if emp.image_1920 else False,
                }
                employee_details.append(responseData)
            return request.make_response(
                json.dumps({'status': True, 'message': 'successful', 'data': employee_details}),
                # json.dumps(employee_details),
                headers=[('Content-Type', 'application/json')]
                )
        else:
            return json.dumps({
                'status': False, 
                'message': 'UnSuccessful: No employee data found with your defined filters ',
                'data': employee_details
                })
        
    @validate_token     
    @http.route(['/employee-leave-info'], type='http', auth='none', csrf=False)
    def EmployeeLeaveData(self, **kwargs):
        employee_details = [] # e.g [{'name': 'Maduka Sopulu', 'phone': 0292900}, {}, {}, {}.........{}]
        staff_number, create_date, employee_id, end_date = self.data_validations(kwargs)
        domain = [('active', '=', True)] # gives you all records
        if staff_number:
            domain = domain + [
                ('employee_id.employee_number', '=ilike', staff_number)
            ]
        if create_date:
            domain = domain + [
                ('date_from', '>=', create_date),
            ]
            
        if end_date:
            domain = domain + [
                ('date_to', '<=', end_date),
            ]
        if employee_id:
            domain = domain + [
                ('employee_id', '=', employee_id),
            ]
        leaves = request.env['hr.leave'].sudo().search(domain)
        if leaves:
            for emp in leaves:
                responseData = {
                    'id': emp.id,
                    'employee_id': emp.employee_id.id,
                    'company_id': emp.company_id.id,
                    'company_name': emp.company_id.name,
                    'full_name': emp.employee_id.name,
                    'work_email': emp.employee_id.work_email,
                    'staff_number': emp.employee_id.employee_number,
                    'job_position_id': emp.employee_id.job_id.id,
                    'job_position_name': emp.employee_id.job_id.name,
                    'employee_date': datetime.strftime(emp.employee_id.first_contract_date, '%d/%m/%Y') if emp.employee_id.first_contract_date else False,
                    'erp_create_date': datetime.strftime(emp.employee_id.create_date, '%d/%m/%Y') if emp.employee_id.create_date else False,
                    'department_id': emp.employee_id.department_id.id,
                    'department_name': emp.employee_id.department_id.name,
                    'district_id': emp.employee_id.branch_id.id,
                    'district_name': emp.employee_id.branch_id.name,
                    'description': emp.name,
                    'duration': emp.duration_display,
                    # 'start_date': emp.date_from,
                    # 'end_date': emp.date_to,
                    
                    'start_date': emp.date_from.strftime('%d/%m/%Y %H:%M:%S') if emp.date_from else False,
                    'end_date': emp.date_to.strftime('%d/%m/%Y %H:%M:%S') if emp.date_to else False,
                    'leave_status': 'Approved' if emp.state in ['validate', 'validate1'] \
                        else 'Submitted' if emp.state in ['draft'] else 'To be Approved' if emp.state in ['confirm'] else 'Refused',
                }
                employee_details.append(responseData)
            return request.make_response(
                json.dumps({'status': True, 'message': 'successful', 'data': employee_details}),
                headers=[('Content-Type', 'application/json')]
                )
        else:
            return json.dumps({
                'status': False, 
                'message': 'UnSuccessful: No leave data found with your defined filters ',
                'data': employee_details
                })
        
    
    @validate_token
    @http.route(['/api/eedc/get-item'], type="http", methods=["GET"], website=True, csrf=False, auth="none")
    def get_eedc_item(self, **kwargs):
        """For Feeder Config"""
        '''
        {'params': {
                'item_id': 1 or null
                'due_for_maintenance': true or false
            }
        }
        if  id, returns the specific config by id else returns all config
        '''
        # try: 
        # req_data = json.loads(request.httprequest.data) # kwargs 
        data = request.params
        item_id = int(data.get('item_id')) if data.get('item_id') else False 
        due_for_maintenance = True if data.get('due_for_maintenance') in [True, 'true', 'True'] else False 
        _logger.info(f"KWARGS thingd {kwargs} DATA {data} VALUE OF config IS {data.get('item_id')} and type {type(data)} {data.keys()}")
        domain = []
        if due_for_maintenance:
            domain.append(('due_for_maintenance', '=', due_for_maintenance))
        if item_id:
            domain.append(('id', '=', item_id))
        config = request.env['feeder.config'].sudo().search(domain)
        if config:
            config_data = []
            for prd in config:
                config_data.append({
                    'record_id': prd.id, 'name': prd.item_id.name, 
                    'injection_id': prd.injection_id.id, 'district_id': prd.district_id.id, 
                    'injection_substation_name': prd.injection_id.name, 'district_name': prd.district_id.name, 
                    'reoccurance_type': prd.reoccurance_type, 
                    'active': prd.active, 'status': prd.status, 
                    'due_for_maintenance': prd.due_for_maintenance, 'status': prd.status, 
                    # 'next_maintenance_date': prd.next_maintenance_date,
                })
            _logger.info(config_data)
            return json.dumps({
                'success': True, 
                'data':config_data
                })
        else:
            return json.dumps({
                'success': False, 
                'message': 'No item found'})  
        
        # except Exception as e:
        #     return json.dumps({
        #             'success': False, 
        #             'message': str(e)})   
    
    @validate_token
    @http.route(['/api/eedc/get-substation'], type="http", methods=["GET"], website=True, csrf=False, auth="none")
    def get_eedc_subStation(self, **kwargs):
        '''
        {'params': {
                'substation_id': 1 or null
            }
        }
        if  id, returns the specific substation by id else returns all substation
        '''
        try: 
            # req_data = json.loads(request.httprequest.data) # kwargs 
            data = request.params
            substation_id = int(data.get('substation_id')) if data.get('substation_id') else False 
            domain = [('id', '=', substation_id)] if substation_id else []
            substations = request.env['injection.model'].sudo().search(domain)
            if substations:
                data = []
                for prd in substations:
                    data.append({
                        'id': prd.id, 'name': prd.name, 
                    })
                return json.dumps({
                    'success': True, 
                    'data':data
                    })
            else:
                return json.dumps({
                    'success': False, 
                    'message': 'No substations found'})  
        except Exception as e:
            return json.dumps({
                    'success': False, 
                    'message': str(e)})
            
            
    @validate_token
    @http.route(['/api/eedc/get-checklist'], type="http", methods=["GET"], website=True, csrf=False, auth="none")
    def get_eedc_checklist(self, **kwargs):
        """For Feeder Config"""
        '''
        {
            'checklist_id': 1,
            # 'create_user_id': 1, # required
            # 'access_user_ids': [1] # required
        }
        if  id, returns the specific checklist by id else returns all checklist
        '''
        # try: 
            # req_data = json.loads(request.httprequest.data) # kwargs 
        data = request.params
        _logger.info(f"CHECKER {data} or {kwargs}") 
        checklist_id = False
        access_user_ids = []
        create_user_id = False
        if data.get('checklist_id'):
            checklist_id = int(data.get('checklist_id'))
            _logger.info(f"CHECKERz {data.get('checklist_id')}") 
            
        if data.get('create_user_id'):
            create_user_id = int(data.get('create_user_id')) 
            
        if data.get('access_user_ids'):
            access_user_ids = [int(r) for r in data.get('access_user_ids')]
        # checklist_id = int(data.get('checklist_id')) if data.get('checklist_id') else False 
        # access_user_ids = [int(r) for r in data.get('access_user_ids')] if data.get('access_user_ids') else []
        # _logger.info(f"KWARGS {kwargs.get('params').get('checklist_id')} DATA {data} VALUE OF config IS {data.get('checklist_id')} and type {type(data)} {data.keys()}")
        domain = []
        if checklist_id:
            domain = [
                ('id', '=', checklist_id), 
                # '|', ('create_uid', '=', create_user_id),
                # ('approver_ids.id', 'in', access_user_ids),
                ] 
        # else:
        #     domain = [
        #         '|', ('create_uid', '=', create_user_id),
        #         ('approver_ids.id', 'in', access_user_ids),
        #         ] 
        checklist = request.env['feeder.checklist'].sudo().search(domain)
        _logger.info(f"KWARGS CHHEC {checklist} DOMMT {domain}")
        
        if checklist:
            data = []
            for prd in checklist:
                data.append({
                    'record_id': prd.id, 'name': prd.name, 
                    'reject_reason': prd.reject_reason, 'description': prd.description, 
                    'feeder_config_id': prd.feeder_config_id.id, 'maintained_by': prd.maintained_by.id, 
                    'feeder_config_name': prd.feeder_config_id.item_id.name, 'maintained_by': prd.maintained_by.name, 
                    # 'maintain_date': prd.maintain_date,
                    'check_lines': [{
                        'id': tx.id,
                        'name': tx.name,
                        'checked': tx.checked,
                    } for tx in prd.checklist_line_ids]
                })
            return json.dumps({
                'success': True, 
                'data':data
                })
        else:
            return json.dumps({
                'success': False, 
                'message': 'No item found'})  
        
        # except Exception as e:
        #     return json.dumps({
        #             'success': False, 
        #             'message': str(e)})    
            
            
    @http.route('/api/eedc/post-checklist', type='json', auth='none', methods=['POST', 'GET'], csrf=False, website=True)
    def post_checklist(self, **kwargs):
        '''
            payload = {
                "operation": 'create' // 'create' or 'update'
                "checklist_id": 2, //required if operation is update,
                "name": 'Anything',
                "description": 'test for api',
                "substation_id": 2, required
                "maintained_by": 2, // user id,
                "maintain_date": "06-06-2023", 
                "checklist_line_ids": [
                {'name': 'xxxxxxxx', 'checked': true}, 
                {'name': 'xxxxxxxx', 'checked': true},
                ...]
            }
        '''
        
        data = json.loads(request.httprequest.data.decode("utf8"))
        # check_list_id = int(data.get('checklist_id'))
        check_list_id_raw = data.get('checklist_id')
        operation = data.get('operation')
        maintained_by = data.get('maintained_by')
        
        _logger.info(f"tester finish {data.get('checklist_line_ids')}")
        # if not data.get('feeder_config_id'):
        if not data.get('substation_id'):
            return {
                'success': False, 
                'message': 'No item found'
            }
        if operation not in ['update', 'create']:
            return {
                'success': False, 
                'message': 'operation must be provided with a value set as update or create'
            }
            
        if not maintained_by:
            return {
                    'success': False,  'message': """Please provide 'maintained_by value'  You must provide the user who maintained the item:"""
                }
        if maintained_by and not request.env['res.users'].search([('id', '=', int(maintained_by))], limit=1):
            return {
                'success': False, 
                'message': """ Please provide correct user id for 'maintained_by value' You must provide the user who maintained the item:"""
            }
            
        feeder_checklist = False
        status= data.get('state')
        if operation == "update":
            if not check_list_id_raw:
                return {
                    'success': False,
                    'message': 'Checklist ID is required for an update operation.'
                }
            else:
                check_list_id = int(check_list_id_raw)
            feeder_checklist = request.env['feeder.checklist'].sudo().search([
            ('id', '=', check_list_id)], limit=1)
            ## update if checklistid
            if feeder_checklist.state in ['Completed']: 
                return {
                    'success': False, 
                    'message': """
                    This maintenance cannot be updated because the state is now completed and closed"""
                }
            # do update here 
            feeder_checklist.checklist_line_ids = [(3, r.id) for r in feeder_checklist.checklist_line_ids]
            payload = {
            # "checklist_id": int(data.get('checklist_id')), 
            # "operation": data.get('operation'),
            "name": data.get('name'),
            "description": data.get('description'),
            # "feeder_config_id": int(data.get('feeder_config_id')) if data.get('feeder_config_id') else False,
            "substation_id": int(data.get('substation_id')), 
            "maintained_by": int(data.get('maintained_by')),
            "maintain_date": data.get('maintained_date') if data.get('maintained_date') else fields.Date.today(),
            # "state": status, # ['Todo', 'In progress', 'Rejected', 'Completed'],
            "checklist_line_ids": [
                 (0, 0, line) for line in data.get('checklist_line_ids')
                  ]
            }
            feeder_checklist.sudo().update(payload)
            if status == 'Completed':
                # if feeder_checklist.feeder_config_id:
                #     feeder_checklist.feeder_config_id.update({
                #         'due_for_maintenance': False,
                #     })
                if feeder_checklist.substation_id:
                    feeder_checklist.substation_id.update({
                    'due_for_maintenance': False,
                })
                feeder_checklist.compute_operations()
            return {
                'success': True, 
                'message': 'Checklist updated successfully',
                'data': {'checklist_id': feeder_checklist.id}
            }
        else:
            # create
            check_list_id = None
            feeder_checklist = request.env['feeder.checklist'].sudo()
            # config = request.env['feeder.config'].sudo().search([('id', '=', int(data.get('feeder_config_id')))])
            config = request.env['injection.model'].sudo().search([('id', '=', int(data.get('substation_id')))])
            feeder_checklist = request.env['feeder.checklist'].sudo()
            payload = {
                "name": data.get('name'),
                "description": data.get('description'),
                # "feeder_config_id": int(data.get('feeder_config_id')),
                "substation_id": int(data.get('substation_id')), 
                "item_id": config.item_id.id if config and config.item_id else False, 
                # "injection_id": config.injection_id.id if config.injection_id else False, 
                "district_id": config.district_id.id if config.district_id else False, 
                "maintained_by": int(data.get('maintained_by')),
                "maintain_date": data.get('maintained_date') if data.get('maintained_date') else fields.Date.today(),
                "state": 'In progress', 
                "checklist_line_ids": [
                    (0, 0, line) for line in data.get('checklist_line_ids')
                    ]
            }
            feeder_checklist.create(payload)
            if status == 'Completed':
                if feeder_checklist.substation_id:
                    feeder_checklist.substation_id.update({
                    'due_for_maintenance': False,
                })
                feeder_checklist.compute_operations(
                    state=status,
                    maintain_date = data.get('maintained_date')
                    
                    )
            # return json.dumps({
            return {'success': True, 
                'message': 'Successfully generated',
                'data': {'checklist_id': feeder_checklist.id}
                }
        _logger.info(f"checklist genereate => {feeder_checklist}")
        
    @http.route('/api/eedc/checklist-approve', type='json', auth='none', methods=['POST', 'GET'], csrf=False, website=True)
    def approve_checklist(self, **kwargs):
        # payload = {
        #     "checklist_id": 2, required not if operation is update
        #     "approved_by": 2, user that does the approval
        # }
        data = json.loads(request.httprequest.data.decode("utf8"))
        if not data.get('checklist_id'):
            return {
                'success': False, 
                'message': 'Please provide checklist ID'
            } 
        check_list_id = int(data.get('checklist_id'))
        approved_by = data.get('approved_by')
        if not approved_by:
            return {
                    'success': False,  'message': """Please provide 'approved_by' value.  You must provide the user who approved the item:"""
                }
        if approved_by and not request.env['res.users'].search([('id', '=', int(approved_by))], limit=1):
            return {
                'success': False, 
                'message': """ Please provide correct user id for 'maintained_by value' You must provide the user who approved the item:"""
            }
        feeder_checklist = request.env['feeder.checklist'].sudo().search([
            ('id', '=', check_list_id)], limit=1)
        if not feeder_checklist:
            return {
                'success': False, 
                'message': f'Checklist with ID {check_list_id} not found. Please provide correct checklist ID'
            } 
        else:
            feeder_checklist.approve_checklist()
            return json.dumps({
                    'success': True, 
                    'data': {},
                    'message': 'Checklist record successfully approved'
                })
            
    @http.route('/api/eedc/checklist-reject', type='json', auth='none', methods=['POST', 'GET'], csrf=False, website=True)
    def reject_checklist(self, **kwargs):
        # payload = {
        #     "checklist_id": 2, required not if operation is update
        #     "reject_reason": 2, user that does the approval
        # }
        data = json.loads(request.httprequest.data.decode("utf8"))
        if not data.get('checklist_id'):
            return {
                'success': False, 
                'message': 'Please provide checklist ID'
            } 
        if not data.get('reject_reason'):
            return {
                'success': False, 
                'message': 'Please provide reason for rejection'
            } 
            
        check_list_id = int(data.get('checklist_id'))
        reject_by = data.get('reject_by')
        if not reject_by:
            return {
                    'success': False,  'message': """Please provide 'reject_by' value.  You must provide the user who approved the item:"""
                }
        if reject_by and not request.env['res.users'].search([('id', '=', int(reject_by))], limit=1):
            return {
                'success': False, 
                'message': """ Please provide correct user id for 'maintained_by value' You must provide the user who approved the item:"""
            }
        feeder_checklist = request.env['feeder.checklist'].sudo().search([
            ('id', '=', check_list_id)], limit=1)
        if not feeder_checklist:
            return {
                'success': False, 
                'message': f'Checklist with ID {check_list_id} not found. Please provide correct checklist ID'
            } 
        else:
            feeder_checklist.reject_checklist(reject_reason = data.get('reject_reason'))
            return json.dumps({
                    'success': True, 
                    'data': {},
                    'message': 'Checklist record successfully approved'
                })
            
    @validate_token
    @http.route(['/api/eedc/get-substations'], type="http", methods=["GET"], website=True, csrf=False, auth="none")
    def get_substations(self, **kwargs):
        """Fetch substations based on provided filters."""
        data = request.params
        _logger.info(f"SUBSTATION REQUEST DATA: {data}")
        
        substation_id = data.get('substation_id')
        district_id = data.get('district_id')
        
        domain = []
        if substation_id:
            domain.append(('id', '=', int(substation_id)))
        if district_id:
            domain.append(('district_id', '=', int(district_id)))
        
        substations = request.env['injection.model'].sudo().search(domain)
        
        if substations:
            result = []
            for sub in substations:
                result.append({
                    'record_id': sub.id,
                    'name': sub.name,
                    'legacy_system_id': sub.legacy_id,
                    'substation_type': sub.substation_type,
                    'substation_status': sub.substation_status,
                    'district_id': sub.district_id.id if sub.district_id else None,
                    'district_name': sub.district_id.name if sub.district_id else None,
                    'next_maintenance_date': sub.next_maintenance_date.strftime('%Y-%m-%d') if sub.next_maintenance_date else "",
                    'previous_maintenance_date': sub.previous_maintenance_date.strftime('%Y-%m-%d') if sub.next_maintenance_date else "",
                    'reoccurance_type': sub.reoccurance_type,
                    'reoccurance_period': sub.reoccurance_period,
                    'due_for_maintenance': sub.due_for_maintenance,
                    'active': sub.active,
                    'status': sub.status,
                })
            return json.dumps({'success': True, 'data': result})
        else:
            return json.dumps({'success': False, 'message': 'No substation found'})

        
    @http.route('/api/eedc/maintenance-summary', type='json', auth='none', methods=['POST'], csrf=False)
    @validate_token
    def maintenance_summary(self, **kwargs):
        """
        Returns summary counts for maintenance checklists.
        
        Optional URL parameters:
        - month: Filter by month in YYYY-MM format (filters on maintain_date)
        - district_id: Filter by a specific district (feeder.checklist.district_id)
        - substation_id: Filter by substation (assumed on feeder_config_id.substation_id)
        """
        data = request.params
        domain = []
        
        # Filter by month if provided
        month_filter = data.get('month')  # Expected format: YYYY-MM
        if month_filter:
            try:
                year, month = map(int, month_filter.split('-'))
                start_date = date(year, month, 1)
                # Compute end date (last day of the month)
                if month == 12:
                    end_date = date(year + 1, 1, 1) - timedelta(days=1)
                else:
                    end_date = date(year, month + 1, 1) - timedelta(days=1)
                domain += [('maintain_date', '>=', start_date), ('maintain_date', '<=', end_date)]
            except Exception as e:
                return {
                    "success": False,
                    "message": "Invalid month format. Expected YYYY-MM."
                }
        
        # Filter by district if provided
        district_id = data.get('district_id')
        if district_id:
            domain += [('district_id', '=', int(district_id))]
        
        # Filter by substation if provided (assumes feeder_config_id has a substation_id field)
        substation_id = data.get('substation_id')
        if substation_id:
            domain += [('substation_id', '=', int(substation_id))]
        
        checklist_obj = request.env['feeder.checklist'].sudo()
        
        # Total counts based on state
        total_count = checklist_obj.search_count(domain)
        total_rejected = checklist_obj.search_count(domain + [('state', '=', 'Rejected')])
        total_approved = checklist_obj.search_count(domain + [('state', '=', 'Completed')])
        total_todo = checklist_obj.search_count(domain + [('state', '=', 'Todo')])
        total_in_progress = checklist_obj.search_count(domain + [('state', '=', 'In progress')])
        
        percentage_completed = (total_approved * 100.0 / total_count) if total_count else 0
        
        # Recent activity: last 5 checklists ordered by maintain_date descending
        recent_checklists = checklist_obj.search(domain, order='maintain_date desc', limit=5)
        recent_activity = []
        for rec in recent_checklists:
            recent_activity.append({
                "checklist_id": rec.id,
                "name": rec.name,
                "maintain_date": rec.maintain_date,
                "maintained_by": rec.maintained_by.name if rec.maintained_by else ""
            })
        
        # Approval list: Approved checklists (state 'Completed')
        approved_records = checklist_obj.search(domain + [('state', '=', 'Completed')], order='approved_date desc')
        approval_list = []
        for rec in approved_records:
            approval_list.append({
                "checklist_id": rec.id,
                "name": rec.name,
                "approved_date": rec.approved_date,
                "approved_by": rec.approved_by.name if rec.approved_by else ""
            })
        
        # Rejected list: Rejected checklists (state 'Rejected')
        rejected_records = checklist_obj.search(
            domain + [('state', '=', 'Rejected')], 
            order='rejected_date desc')
        rejected_list = []
        for rec in rejected_records:
            rejected_list.append({
                "checklist_id": rec.id,
                "name": rec.name,
                "rejected_date": rec.rejected_date,
                "rejected_by": rec.rejected_by.name if rec.rejected_by else "",
                "reject_reason": rec.reject_reason
            })
        
        return {
            "success": True,
            "counts": {
                "total_rejected": total_rejected,
                "total_approved": total_approved,
                "total_todo": total_todo,
                "total_in_progress": total_in_progress,
                "total_count": total_count,
                "percentage_completed": percentage_completed,
            },
            "recent_activity": recent_activity,
            "approval_list": approval_list,
            "rejected_list": rejected_list,
        }
       
    ##### odoo artifacts ########
    @http.route('/api/inv', type='json', auth='none', methods=['POST', 'GET'], csrf=False, website=True)
    def validate_inv(self, **kwargs):
        data = json.loads(request.httprequest.data.decode("utf8"))
        inv = request.env['account.move'].sudo().search([
            '|', ('name', '=', data.get('invoice_number')), 
            ('id', '=', data.get('invoice_id'))], limit=1)
        _logger.info(f"INVOICES => {inv}")
        
    @http.route('/api/v1/inv', type='json', auth='none', methods=['POST', 'GET'], csrf=False, website=True)
    def validate_invoice_api(self, **kwargs):
        
        '''url = "http://localhost:8069/api/v1/invoice-validation"
        User must provide either invoice_number or invoice_id
        payload = {
            "invoice_number": "INV/2024/00001",
            "invoice_id": 2, # 
            "is_register_payment": True or False, # 
            "journal_id": Null or Not Null, Not null if is_register_payment is True# 
        }'''
        # data = json.loads(request.httprequest.data)
        # data = request.params
        data = json.loads(request.httprequest.data.decode("utf8"))
        _logger.info(f"Data is {data}")
        
        invoice_number = data.get('invoice_number')
        invoice_id = int(data.get('invoice_id')) if data.get('invoice_id') else False
        journal_id = int(data.get('journal_id')) if data.get('journal_id') else False
        is_register_payment = data.get('is_register_payment')
        if not invoice_number or not invoice_id: 
            json.dumps({
                    'success': False, 
                    'data': {},
                    'message': 'Please provide invoice id or invoice number'
                })
        journalid = None
        if is_register_payment:
            if not journal_id:
                json.dumps({
                    'success': False, 
                    'data': {},
                    'message': 'Please add a valid journal id'
                })
            journal = request.env['account.journal'].sudo().search([('id', '=', int(journal_id))], limit=1)
            if not journal:
                json.dumps({
                    'success': False, 
                    'data': {},
                    'message': 'No journal found'
                })
            journalid = journal.id
        inv = request.env['account.move'].sudo().search([
            '|', ('name', '=', invoice_number), 
            ('id', '=', invoice_id)], limit=1)
        _logger.info(f"Data INVOICE is {inv}")
        
        if inv:
            if inv.state == "draft":
                _logger.info(f"bolo {inv}")
                
                # inv.action_post()
                inv.action_post()
                # inv.message_post(body='Invoice Generated from api',
                #               message_type='comment',
                #               subtype_xmlid='mail.mt_note',
                #               author_id=request.env.user.partner_id.id)
        
            payment = None
            # journalid = request.env['account.journal'].sudo().browse([8])
            # _logger.info(f"Data JOURNAL INV TO VALIDATE is {journalid}")
            # if is_register_payment:
            
                # payment = self.validate_invoice_and_post_journal(journalid, inv)
                
            # else:
            return json.dumps({
            'success': True, 
            'message': 'Successfully generated',
            'data': {'invoice_id': inv.id, 'invoice_number': inv.name}
            })
        else:
            return json.dumps({
                    'success': False, 
                    'data': {},
                    'message': 'No invoice found'
                    }) 
            
    # @http.route('/api/get-product', type='json', auth='none', methods=['GET'], csrf=False)
    @validate_token
    @http.route(['/api/get-product'], type="http", methods=["GET"], website=True, csrf=False, auth="none")
    def get_products(self, **kwargs):
        '''
        {'params': {
                'product_id': 1 or null
            }
        }
        if product id, returns the specific product by id else returns all products
        '''
        try: 
            # req_data = json.loads(request.httprequest.data) # kwargs 
            data = request.params
            product_id = int(data.get('product_id')) if data.get('product_id') else False 
            _logger.info(f"KWARGS {kwargs} DATA {data} VALUE OF PRODUCT IS {data.get('product_id')} and type {type(data)} {data.keys()}")
            # if product_id and type(product_id) != int:
            #     return invalid_response(
            #         "Product id",
            #         "Product ID provided must be an integer"
            #         "[product_id]",
            #         400,
            #     )
            domain = [('id', '=', product_id)] if product_id else []
            products = request.env['product.product'].sudo().search(domain)
            if products:
                data = []
                for prd in products:
                    data.append({
                        'id': prd.id, 'name': prd.name, 'sale_price': prd.list_price,
                        'image': f'/web/image/product.product/{prd.id}/image_512',
                        'product_uom': request.env.ref('uom.product_uom_categ_unit').id,
                        'taxes': [{
                            'id': tx.id,
                            'name': tx.name,
                            'value': tx.amount,
                            'tax_type': tx.amount_type, # e.g percent, fixed
                        } for tx in prd.taxes_id]
                    })
                return json.dumps({
                    'success': True, 
                    'data':data
                    })
            else:
                return json.dumps({
                    'success': False, 
                    'message': 'No product found'})  
        
        except Exception as e:
            return json.dumps({
                    'success': False, 
                    'message': str(e)})
    
    @validate_token  
    @http.route('/api/get-product-availability', type='http', auth='none', methods=['GET'], csrf=False,  website=True)
    def get_product_availability(self, **kwargs):
        '''
        {
            'product_id': 10,
            'requesting_qty': 2, # pass the requesting quantity
        }
        if product id, returns the specific product quantities based on the user company warehouse
        '''
        _logger.info(f"TESTTINGN {request.params}") 
        try:
            # req_data = json.loads(request.httprequest.data) # kwargs
            data = request.params # kwargs# req_data.get('params')
            
            _logger.info(f" PROFDUCEUS ==> {data} ==>>")
            
            product_id = int(data.get('product_id')) if data.get('product_id') else False
            qty = int(data.get('requesting_qty'))
            _logger.info(f" TRYINGGGGGGGGGGGGE ==> {data} ==>> QTY {qty} ===> PRODUCT TYPE {type(product_id)}")
            # if product_id and type(product_id) not in ['int', int]:
            #     _logger.info(f" PRODUCT TYPE IS type(f'{type(product_id)}")
            #     return json.dumps({
            #             "success": False,
            #             "data": {},
            #             "message": "Wrong Product id format sent", 
            #             })
            domain = [('active', '=', True),('id', '=', product_id)]
            product = request.env['product.product'].sudo().search(domain, limit=1)
            if product:
                warehouse_domain = [('company_id', '=', request.env.user.company_id.id)]
                warehouse_location_id = request.env['stock.warehouse'].sudo().search(warehouse_domain, limit=1)
                stock_location_id = warehouse_location_id.lot_stock_id
                # should_bypass_reservation : False
                if product.detailed_type in ['product']:
                    total_availability = request.env['stock.quant'].sudo()._get_available_quantity(product, stock_location_id, allow_negative=False) or 0.0
                    product_qty = float(qty) if qty else 0
                    if product_qty > total_availability:
                        return json.dumps({
                            "success": False,
                            "data": {'total_quantity': total_availability},
                            "message": f"Selected product quantity ({product_qty}) is higher than the Available Quantity. Available quantity is {total_availability}", 
                            })
                    else:
                        return json.dumps({
                            "status": True,
                            "message": "The requesting quantity of Product is available", 
                        })
                else:
                    return json.dumps({
                        "status": False,
                        "message": "Product selected for check must be a storable product and not service", 
                        })
            else:
                return json.dumps({
                    'success': False, 
                    'message': 'No product found'})  
        
        except Exception as e:
            return json.dumps({
                    'success': False, 
                    'message': str(e)
                    })
            
    @validate_token
    @http.route(['/api/get-available-drivers'], type="http", methods=["GET"], website=True, csrf=False, auth="none")
    def get_available_products(self, **kwargs):
        """
        Returns list of all available drivers
        Payload: 
        
        DRIVER_DATA = {
        "id": None,
        }
        """
        try: 
            data = request.params
            _logger.info(f"Returning all drivers available")
            domain = [('is_delivery_person', '=', True),('is_available', '=', True)]
            driver_id = data.get('id')
            _logger.info(f"GETTING USERS drivers {driver_id} and {domain} // {type(driver_id)}") 
            if driver_id:
                # type(driver_id) not in [int,float]
                if not driver_id.isdigit() or driver_id in ['False', False, 'None']:
                    return json.dumps({
                    'success': False,
                    'message': 'id must be of type integer or none'
                    })
                domain.append(('id', '=',  int(data.get('id'))))
            delivery_men = request.env['res.users'].sudo().search(domain)
            if delivery_men:
                data = []
                for usr in delivery_men:
                    data.append({
                        'id': usr.id, 'name': usr.name, 'phone': usr.phone or usr.partner_id.phone,
                        'email': usr.email, 'email2': usr.partner_id.email, 'mobile': usr.partner_id.mobile,
                        'image': f'/web/image/res.users/{usr.id}/image_1920',
                    })
                return json.dumps({
                    'success': True, 
                    'data':data,
                    'message': 'All partner record retrieved'
                    })
            else:
                return json.dumps({
                    'success': False, 
                    'message': 'No user found as a delivery person'
                    })  
        
        except Exception as e:
            return json.dumps({
                    'success': False, 
                    'message': str(e)})
        
    @validate_token    
    @http.route('/api/get-branch', type='http', auth='none', methods=['GET'], csrf=False, website=True)
    def get_branch(self, **kwargs):
        '''
        {'params':{
            'branch_id': 1 or null
        }
        if product id, returns the specific product by id else returns all products
        '''
        try:
            # req_data = json.loads(request.httprequest.data) # kwargs
            # data = json.loads(request.httprequest.data) # kwargs 
            data = request.params # req_data.get('params')
            branch_id = int(data.get('branch_id')) if data.get('branch_id') else False
            # if branch_id and type(branch_id) != int:
                # return invalid_response(
                #     "branch id",
                #     "branch ID provided must be an integer"
                #     "[branch_id]",
                #     400,
                # )
            domain = [('id', '=', branch_id)] if branch_id else []
            branch = request.env['multi.branch'].sudo().search(domain)
            if branch:
                data = []
                for prd in branch:
                    data.append({
                        'id': prd.id, 'name': prd.name
                    })
                return json.dumps({
                    'success': True, 
                    'data':data
                    })
            else:
                return json.dumps({
                    'success': False, 
                    'message': 'No branch found'})
        
        except Exception as e:
            return json.dumps({
                    'success': False, 
                    'message': str(e)})
            
    @validate_token
    @http.route('/api/delivery/acknowledge', type='http', auth='none', methods=['GET', 'POST'], csrf=False)
    def get_contacts(self, **kwargs): 
        '''
        headers = {
            'Content-Type': 'application/json', # use if type of request is json
            'token': 'token_sasdd7e6ca6e3793e40bd6171429de6f8686ac6cd',
            #'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
             # use if type of request is http
            #'Cookie': 'session_id=3cc87cdab877e01940c841e98e337bf291c180c1',
                }
        # {'params': {
            {
            'stock_id': 1 or null,
            'stock_number': 1 or null,
            'note': "i have acknowledged it",
        }
        # }
        if stock id, use the stock id to send the data as acknowledged
        '''
        try:
            # req_data = json.loads(request.httprequest.data) # kwargs 
            # data = req_data.get('params')
            data = request.params # stock_id, stock_number, note
            stock_id = int(data.get('stock_id')) if data.get('stock_id') else False
            stock_number = data.get('stock_number')
            note = data.get('note')
            
            domain = ['|', ('id', '=', stock_id), ('name', '=', stock_number)] if stock_id or stock_number else [('id', '=', 0)]
            stock = request.env['stock.picking'].sudo().search(domain)
            if (not stock): 
                return json.dumps({
                'success': False, 
                'message': 'Please provide a valid stock id or stock number'
                })
            else:
                acknowledge_val = {
                    'acknowledge_note': note, 
                    'is_acknowledge': True,
                }
                stock_val = request.env['stock.picking'].sudo().write(acknowledge_val)
                return json.dumps({
                    'success': True, 
                    'data': stock.name
                    })
        
        except Exception as e:
            return json.dumps({
                    'success': False, 
                    'message': str(e)
            })
    
    @validate_token
    @http.route('/api/contact-operation', type='http', auth='none', methods=['GET', 'POST'], csrf=False)
    def get_contacts(self, **kwargs): 
        '''
        headers = {
            'Content-Type': 'application/json', # use if type of request is json
            'token': 'token_sasdd7e6ca6e3793e40bd6171429de6f8686ac6cd',
            #'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
             # use if type of request is http
            #'Cookie': 'session_id=3cc87cdab877e01940c841e98e337bf291c180c1',
                }
        # {'params': {
            {
            'contact_id': 1 or null,
            'contact_name': Moses Abraham or null,
            'id': cnt.id, 
            'to_create_contact': True, # (creates a new contact if contact id or name is not found), 
            'contact_name': 'peter Maduka Sopulu' or None, 
            'address1': 'No. 45 Maduka Sopulu Street'
            'address2': 'No. 46 Maduka Sopulu Street'
            'phone': '09092998888',
            'email': 'maduka@gmail.com',
        }
        # }
        if contact id, returns the specific contact by id else returns all contacts
        '''
        try:
            # req_data = json.loads(request.httprequest.data) # kwargs
            
            # data = req_data.get('params')
            data = request.params
            contact_id = int(data.get('contact_id')) if data.get('contact_id') else False
            address1 = data.get('address1')
            address2 = data.get('address2')
            phone = data.get('phone')
            email = data.get('email')
            contact_name = data.get('contact_name')
            to_create_contact = data.get('to_create_contact')
            # if contact_id and type(contact_id) != int:
            #     return invalid_response(
            #         "contact id",
            #         "contact ID provided must be an integer"
            #         "[contact_id]",
            #         400,
            #     )
            domain = ['|', ('id', '=', contact_id), ('name', '=', contact_name)] if contact_id or contact_name else []
            contact = request.env['res.partner'].sudo().search(domain)
            address = address1 or address2
            if (not contact) and to_create_contact:
                if not contact_name or not address or not phone or not email:
                    return json.dumps({
                    'success': False, 
                    'message': 'Please provide the following fields; contact name, address, phone and email'
                    })
                contact_vals = {
                    'name': contact_name, 
                    'street': address1, 
                    'street2': address2,
                    'phone': phone,
                    'email': email,
                }
                contact = request.env['res.partner'].sudo().create(contact_vals)
            if contact:
                data = []
                for cnt in contact:
                    data.append({
                        'id': cnt.id, 
                        'contact_name': cnt.name or None, 
                        'address1': cnt.street or None, 
                        'address2': cnt.street2 or None,
                        'phone': cnt.phone or None,
                        'email': cnt.email or None,
                    })
                return json.dumps({
                    'success': True, 
                    'data':data
                    })
            else:
                return json.dumps({
                    'success': False, 
                    'message': 'No contact found on the system'}) 
        
        except Exception as e:
            return json.dumps({
                    'success': False, 
                    'message': str(e)})
            
    @validate_token   
    @http.route('/api/get-users', type='http', auth='none', methods=['GET'], csrf=False)
    def get_users(self, **kwargs):
        '''
        {'params': {
            'user_id': 1 or null
            'user_name': Moses Abraham or null
        }}
        if user id or user name, returns the specific contact by id  or name else returns all contacts
        '''
        try:
            # req_data = json.loads(request.httprequest.data) # kwargs 
            # data = req_data.get('params')
            data = request.params
            user_id = int(data.get('user_id')) if data.get('user_id') else False
            user_name = data.get('user_name')
            if not user_id:
                return json.dumps({'success': False,  'message': 'No user found on the system'})
            domain = ['|', ('id', '=', user_id), ('name', '=', user_name)] if user_id or user_name else []
            users = request.env['res.users'].sudo().search(domain)
            if users:
                data = []
                for usr in users:
                    data.append({
                        'id': usr.id, 
                        'user_name': usr.name or None,
                    })
                return json.dumps({
                    'success': True, 
                    'data':data
                    })
            else:
                return json.dumps({
                    'success': False, 
                    'message': 'No user found on the system'})
        
        except Exception as e:
            return json.dumps({
                    'success': False, 
                    'message': str(e)}) 
            
    @validate_token   
    @http.route('/api/get/invoice', type='http', auth='none', methods=['GET'], csrf=False)
    def api_get_invoice(self, **kwargs):
        ''''''
        # data = json.loads(request.httprequest.data.decode("utf8"))
        data = request.params 
        _logger.info(f"TESTTINGN {data}") 
        
        '''
        headers = {
            'Content-Type': 'application/json',
            'token': 'token_sasdd7e6ca6e3793e40bd6171429de6f8686ac6cd',
            #'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
                    #'Cookie': 'session_id=3cc87cdab877e01940c841e98e337bf291c180c1',
                        }
        INV = {
                "invoice_id": '1', # USE IF YOU WANT TO GET THE INVOICE NUMBER USING ID REFERENCE FROM THE BACKEND
                "invoice_number": 'INV/A00/1233', # USE EITHER INVOICE NUMBER TO GET THE INVOICE NUMBER DIRECTLY
                "so_number": False, # TO BE USED IF YOU WANT TO CALL USING SO_NUMBER ONLY, IT RETURNS ALL INVOICES RELATED TO THE SALE ORDER,
                 "partner_id": "1" # 'RETURNS ALL THE INVOICES RELATED TO THIS PARTNER',
                }
            url3 = "http://127.0.0.1:8080/api/get/invoice"
            req = rq.get(url3, headers=headers, json=INV)
        '''
        invoice_id = int(data.get('invoice_id')) if data.get('invoice_id') else False
        partner_id = int(data.get('partner_id')) if data.get('partner_id') else False
        so_number = data.get('so_number')
        invoice_number = data.get('invoice_number')

        if invoice_number or invoice_id or so_number:
            inv = request.env['account.move'].sudo().search([
                '|', ('id', '=', invoice_id),
                ('name', '=', invoice_number)
            ], limit=1)
            if inv:
                order_data = {
                'id': inv.id,
                'name': inv.name,
                'partner_id': inv.partner_id.id,
                'partner_name': inv.partner_id.name,
                'date_order': inv.invoice_date.strftime('%Y-%m-%d %H:%M:%S') if inv.invoice_date else '',
                'invoice_line_ids': [{
                    'product_id': line.product_id.id,
                    'product_name': line.product_id.name,
                    'account_id': line.account_id.id,
                    'account_name': line.account_id.name,
                    'product_uom_id': line.product_uom_id.id,
                    'product_uom_name': line.product_uom_id.name,
                    'quantity': line.quantity,
                    'price_unit': line.price_unit,
                    'price_subtotal': line.price_subtotal,
                    'taxes': [{
                            'id': tx.id,
                            'name': tx.name,
                            'value': tx.amount,
                            'tax_type': tx.amount_type, # e.g percent, fixed
                        } for tx in line.tax_ids]
                    } for line in inv.invoice_line_ids]
                }
                return json.dumps({'success': True, 'result': order_data})
        
        
            elif so_number or partner_id:
                so_order = request.env['sale.order'].sudo().search([
                '|', ('name', '=', so_number),
                ('partner_id', '=', partner_id),
                ], limit=1)

                if not so_order:
                    return json.dumps({'success': False, 'message': 'No invoice found for this sale order nummber or partner id provided'})
        
                order_data = [{
                    'id': inv.id,
                    'name': inv.name,
                    'partner_id': inv.partner_id.id,
                    'partner_name': inv.partner_id.name,
                    'date_order': inv.invoice_date.strftime('%Y-%m-%d %H:%M:%S') if inv.invoice_date else '',
                    'invoice_line_ids': [{
                        'product_id': line.product_id.id,
                        'product_name': line.product_id.name,
                        'account_id': line.account_id.id,
                        'account_name': line.account_id.name,
                        'product_uom_id': line.product_uom_id.id,
                        'product_uom_name': line.product_uom_id.name,
                        'quantity': line.quantity,
                        'price_unit': line.price_unit,
                        'price_subtotal': line.price_subtotal,
                        'taxes': [{
                                'id': tx.id,
                                'name': tx.name,
                                'value': tx.amount,
                                'tax_type': tx.amount_type, # e.g percent, fixed
                            } for tx in line.tax_ids]
                    } for line in inv.invoice_line_ids]
                } for inv in so_order.invoice_ids]
                return json.dumps({'success': True, 'result': order_data})
            else:
                return json.dumps({'success': False, 'message': 'No invoice found with this id or invoice or sale order nummber provided'})
        else:
            invoices = request.env['account.move'].sudo().search([])
            order_data = [{
            'id': inv.id,
            'name': inv.name,
            'partner_id': inv.partner_id.id,
            'partner_name': inv.partner_id.name,
            'date_order': inv.invoice_date.strftime('%Y-%m-%d %H:%M:%S') if inv.invoice_date else '',
            'invoice_line_ids': [{
                'product_id': line.product_id.id,
                'product_name': line.product_id.name,
                'account_id': line.account_id.id,
                'account_name': line.account_id.name,
                'product_uom_id': line.product_uom_id.id,
                'product_uom_name': line.product_uom_id.name,
                'quantity': line.quantity,
                'price_unit': line.price_unit,
                'price_subtotal': line.price_subtotal,
                'taxes': [{
                        'id': tx.id,
                        'name': tx.name,
                        'value': tx.amount,
                        'tax_type': tx.amount_type, # e.g percent, fixed
                    } for tx in line.tax_ids]
                } for line in inv.invoice_line_ids]
            } for inv in invoices]
            return json.dumps({'success': True, 'result': order_data})
            
    @validate_token   
    @http.route('/api/sales_order/operation', type='http', auth='none', methods=['POST', 'GET'], csrf=False)
    def handle_sales_operations(self, **kwargs):
        ''''''
        data = json.loads(request.httprequest.data.decode("utf8"))
         
        # req_data = json.loads(request.httprequest.data) # kwargs
        # req_data = json.loads(request.params) # kwargs
        # data = request.params
        '''
        headers = {
            'Content-Type': 'application/json',
            'token': 'token_sasdd7e6ca6e3793e40bd6171429de6f8686ac6cd',
            #'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
                    #'Cookie': 'session_id=3cc87cdab877e01940c841e98e337bf291c180c1',
                        }
        SALES = {
                "partner_id": "1",
                "operation": "create",
                "company_id": "1",
                "so_number": False,
                "order_id": False,
                "order_lines":
                    [{"product_id": 4, "price_unit": 8500, "product_uom_qty": 4}]
                }
            url3 = "http://127.0.0.1:8080/api/sales_order/operation"
            req = rq.get(url3, headers=headers, json=SALES)
        '''
        
        # try:
        if data.get('operation') == 'create':
            return self._create_sales_order(data)
              
             
        elif data.get('operation') == 'update':
            return self._update_sales_order(data)
        elif data.get('operation') == 'get':
            return self._get_sales_order(data)
        else:
            return json.dumps(
                {'success': False, 
                    'message': 'Ensure that the operation data contains create, update, or get'}
                )  
        
        # except Exception as e:
        #     return json.dumps({'error': str(e)})
        
        
        
    def _create_sales_order(self, data):
        '''where data is equal to the sent payload'''
        partner_id = int(data.get('partner_id')) if data.get('partner_id') else False
        order_lines = data.get('order_lines')
        company_id = int(data.get('company_id')) if data.get('company_id') else 1
        _logger.info(f"Data is {data}")
        _logger.info(f".....Partner_id: {partner_id}, Order Lines: {order_lines} and Company ID: {company_id}.....")
        
        if not partner_id or not order_lines:
            return json.dumps(
                    {'success': False, 
                     'message': 'missing parameter such as partnerid, or orderlines not provided'}
                    )
        order_vals = {
            'partner_id': partner_id,
            'company_id': company_id,
            'order_line': [(0, 0, line) for line in order_lines]
        }
        _logger.info(f"Data XXX is {data}")
        order = request.env['sale.order'].sudo().create(order_vals)
        order.action_confirm()
        inv = order.sudo()._create_invoices()[0]
        return json.dumps({
            'success': True, 
            'data': {
                'so_id': order.id, 'so_id': order.name,
            'invoice_id': inv.id,'invoice_number': inv.name,
            }
            })
    
    def generate_stock_transfer(self, user, **kwargs):
        '''params: kwargs = DELIVERY_TRANSFER = {
                "partner_id": 2,
                "so_id": 2,
                "picking_id": 4,
                "picking_number": "WHOOL/0001",
                "delivery_man_id": "3",
                "order_delivery_status": "progress",
                "so_number": "SO0004",
                "item_ids":
                    [{"name": "S0Q003", "product_id": 4, "location_id": 1, "location_dest_id": 5, "product_uom_qty": 4}]
                }'''
        stock_picking_type_out = request.env.ref('stock.picking_type_out')
        stock_picking = request.env['stock.picking']
        saleOrder = request.env['sale.order']
        picking_so_order = None
        data = kwargs.get('dict_data')
        so_id = data.get('so_id')
        so_number = data.get('so_number')
        picking_id = data.get('picking_id', None)
        delivery_man_id = data.get('delivery_man_id')
        picking_number = data.get('picking_number')
        order_delivery_status = data.get('order_delivery_status')
        partner_id = data.get('partner_id')
        item_ids = data.get('item_ids')
        so_order = saleOrder.search(['|', ('id', '=', so_id), ('name', '=', so_number)], limit=1)
        if so_order and so_order.picking_ids:
            picking_so_order = so_order.picking_ids[0]
        elif picking_number or picking_id:
            existing_picking = stock_picking.search(['|', ('id', '=', picking_id), ('name', '=', picking_number)], limit=1)
            if existing_picking:
                picking_so_order = existing_picking
        
        if not picking_so_order:
            # user = request.env.user
            warehouse_location_id = request.env['stock.warehouse'].search([
                ('company_id', '=', user.company_id.id) 
            ], limit=1)
            destination_location_id = request.env.ref('stock.stock_location_customers')
            vals = {
                'scheduled_date': fields.Date.today(),
                'picking_type_id': stock_picking_type_out.id,
                'origin': so_number,
                'assigned_delivery_man': delivery_man_id,
                'partner_id': partner_id,
                'order_delivery_status': order_delivery_status,
                'move_ids_without_package': [(0, 0, {
                                'name': so_number, 
                                'picking_type_id': stock_picking_type_out.id,
                                'location_id': stock_picking_type_out.default_location_src_id.id or warehouse_location_id.lot_stock_id.id,
                                'location_dest_id': stock_picking_type_out.default_location_dest_id.id or destination_location_id.id,
                                'product_id': mm.get('product_id'),
                                'product_uom_qty': mm.get('quantity'),
                                'quantity': mm.get('quantity'),
                                # 'date_deadline': mm.date_deadline,
                }) for mm in item_ids]
            }
            stock = stock_picking.sudo().create(vals)
            soid = saleOrder.search([('name', '=', stock.origin)], limit=1)
            del_man = request.env['res.users'].sudo().search([('id', '=', delivery_man_id)], limit=1)
            if soid:
                so_order.update({
                'assigned_delivery_man': delivery_man_id
                })
            if del_man:
                del_man.update({
                'is_available': True
                })
        else:
            stock = picking_so_order
            if delivery_man_id:
                stock.update({
                    'assigned_delivery_man': delivery_man_id
                    })
                soid = saleOrder.search([('name', '=', stock.origin)], limit=1)
                del_man = request.env['res.users'].sudo().search([('id', '=', delivery_man_id)], limit=1)
                if soid:
                    so_order.update({
                    'assigned_delivery_man': delivery_man_id
                    })
                if del_man:
                    del_man.update({
                    'is_available': True
                    })
                    
                
            stock.button_validate()
        return stock
    
    @validate_token   
    @http.route('/api/create/delivery', type='http', auth='none', methods=['POST', 'GET'], csrf=False)
    def delivery_operation(self, **kwargs):
         
        # req_data = json.loads(request.httprequest.data) # kwargs
        # req_data = json.loads(request.params) # kwargs
        # data = request.params
        '''
        headers = {
            'Content-Type': 'application/json',
            #'token': 'token_sasdd7e6ca6e3793e40bd6171429de6f8686ac6cd',
            #'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
                    #'Cookie': 'session_id=3cc87cdab877e01940c841e98e337bf291c180c1',
                        }
        DELIVERY_TRANSFER = {
                "partner_id": 2,
                "so_id": 2,
                "picking_id": 4,
                "picking_number": "WHOOL/0001",
                "so_number": "SO0004",
                "item_ids":
                    [{"name": "S0Q003", "product_id": 4, "location_id": 1, "location_dest_id": 5, "product_uom_qty": 4}]
                }
            url3 = "http://127.0.0.1:8080/api/delivery"
            req = rq.get(url3, headers=headers, json=SALES)
        '''
        data = json.loads(request.httprequest.data.decode("utf8"))
        if data: 
            dictdata = dict(
                so_id = data.get('so_id'),
                so_number = data.get('so_number'),
                picking_id = data.get('picking_id'),
                picking_number = data.get('picking_number'),
                partner_id = data.get('partner_id'),
                delivery_man_id = data.get('delivery_man_id'),
                order_delivery_status = data.get('order_delivery_status'),
                item_ids = data.get('item_ids'),
            )
            user = request.env.user
            stock = self.generate_stock_transfer(user, dict_data=dictdata)
            return json.dumps({
                'success': True, 
                'data': {
                    'delivery_id': stock.id, 'delivery_number': stock.name,
                    'delivery_man_id': stock.assigned_delivery_man.id,
                    'delivery_man': stock.assigned_delivery_man.name,
                    'status': stock.state.capitalize(),
                }
            })
        else:
            return json.dumps(
                {'success': False, 
                    'message': 'Ensure that the operation data contains create, update, or get'}
                )  
        
    def validate_invoice_and_post_journal(
        self, journal_id, inv): 
        """To be used only when they request for automatic payment generation
        journal: set to the cash journal default bank journal is 7
        """
        inbound_payment_method = request.env['account.payment.method'].sudo().search(
            [('code', '=', 'manual'), ('payment_type', '=', 'inbound')], limit=1)
        payment_method = 2
        if journal_id:
            payment_method = journal_id.inbound_payment_method_line_ids[0].id if \
                journal_id.inbound_payment_method_line_ids else inbound_payment_method.id \
                    if inbound_payment_method else payment_method
        # payment_method_line_id = request.get_payment_method_line_id('inbound', journal_id)
        payment_vals = {
            'date': fields.Date.today(),
            'amount': inv.amount_total,
            'payment_type': 'inbound',
            'company_id': inv.company_id.id,
            # 'is_internal_transfer': True,
            'partner_type': 'customer',
            'ref': inv.name,
            # 'move_id': inv.id,
            # 'journal_id': 8, #inv.payment_journal_id.id,
            'currency_id': inv.currency_id.id,
            'partner_id': inv.partner_id.id,
            # 'destination_account_id': inv.line_ids[1].account_id.id,
            'payment_method_line_id': payment_method, #payment_method_line_id.id if payment_method_line_id else payment_method,
        }
        _logger.info(f"VALIDATE xxx is {payment_vals}")
        
        '''
        Add the skip context to avoid;  
        Journal Entry Draft Entry PBNK1/2023/00002 is not valid. 
        In order to proceed, the journal items must include one and only
        one outstanding payments/receipts account.
        '''
        skip_context = {
            'skip_invoice_sync':True,
            'skip_invoice_line_sync':True,
            'skip_account_move_synchronization':True,
            'check_move_validity':False,
        }
        # payments = request.env['account.payment'].sudo().with_context(**skip_context).create(payment_vals)
        # # payments = request.env['account.payment'].create(payment_vals)
        # # payments._synchronize_from_moves(False)
        
        # payments.action_post()
        # return payments
       
        
    def _update_sales_order(self, data):
        '''Update an existing sales order.'''
        data.pop('operation', None)
        order_id = int(data.pop('id')) if data.pop('id') else False
        
        order = request.env['sale.order'].sudo().browse(order_id)
        if order:
            order_lines = data.pop('order_lines', None)
            if order_lines:
                updated_order_lines = []
                existing_product_ids = order.order_line.mapped('product_id.id')

                for line in order_lines:
                    product_id = line.get('product_id')
                    
                    if product_id in existing_product_ids:
                        existing_line = order.order_line.search([('order_id', '=', order.id),('product_id.id', '=', product_id)], limit=1)
                        updated_order_lines.append((1, existing_line.id, line))
                    else:
                        updated_order_lines.append((0, 0, line))

                data['order_line'] = updated_order_lines

            order.write(data)
            return json.dumps({'success': True, 'order_id': order.id})
        else:
            return json.dumps({'success': False, 'message': 'Sales order not found'})

    def _get_sales_order(self, data):
        '''where data is equal to the sent payload for get,
        e.g data = { 'id': 3, ...}
        '''
        order_id = int(data.get('id')) if data.get('id') else False
        so_number = data.get('so_number')

        if order_id or so_number:
            order = request.env['sale.order'].sudo().search([
                '|', ('id', '=', order_id), ('name', '=', so_number)
            ], limit=1)

            if not order:
                return {'success': False, 'message': 'Sales order not found'}
            
            order_data = {
                'id': order.id,
                'name': order.name,
                'partner_id': order.partner_id.id,
                'date_order': order.date_order.strftime('%Y-%m-%d %H:%M:%S'),
                'order_line': [{
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.product_uom_qty,
                    'price_unit': line.price_unit
                } for line in order.order_line]
            }
            return json.dumps({'success': True, 'result': order_data})

        return json.dumps({'success': False, 'message': 'Missing order ID or SO number'})
 