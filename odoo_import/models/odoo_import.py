# -*- coding: utf-8 -*-

from odoo.exceptions import ValidationError
from odoo import fields, models, api, _
import ast 
import psycopg2
import logging
_logger = logging.getLogger(__name__)


source_connection = False
target_connection = False

class MaOdooImportLine(models.Model):
    _name = 'ma.import.line'
    _description = 'Import model line'
    
    import_id = fields.Many2one('ma.import', string="Import")
    
    source_column_name = fields.Char(string="Source Column Name")
    source_field_data_type = fields.Char(string="Source Column Data type")
    source_field_foreign_key = fields.Char(string="Source Field Foreign / Relation table")
    
    target_field_id = fields.Many2one('ir.model.fields', string="Target Column Name /Fields")
    target_field_type_id = fields.Char(string="Target field type", compute="compute_target_fields")
    target_field_foreign_key_id = fields.Char(string="Target field Relation", compute="compute_target_fields")
    target_field_required_id = fields.Char(string="Is Target field required", compute="compute_target_fields")

    @api.depends('target_field_id')
    def compute_target_fields(self):
        for r in self:
            if r.target_field_id:
                r.target_field_type_id = r.target_field_id.ttype
                r.target_field_required_id = r.target_field_id.required
                r.target_field_foreign_key_id = r.target_field_id.relation
            else:
                r.target_field_type_id = False
                r.target_field_required_id = False
                r.target_field_foreign_key_id = False


class MaOdooImport(models.Model):
    _name = "ma.import"
    _description = 'Export model'


    name = fields.Char(
        string="Title of Document", 
        help="Display title of the file to generate"
        )
    source_host = fields.Char(
        string="Source Host", 
        placeholder="http://www.smartds.com", 
        required=True)
    source_port = fields.Char(
        string="Source Port", 
        required=True, 
        default="5432"
        )
    source_db_name = fields.Char(
        string="Source DB Name", 
        placeholder="mydatabasename", 
        required=True)
    source_db_user = fields.Char(
        string="Source DB User", 
        required=True)
    source_db_password = fields.Char(
        string="Source DB Password", 
        required=True
        )
    
    target_host = fields.Char(
        string="Target Host", 
        placeholder="http://www.smartds.com", 
        required=True
        )
    target_port = fields.Char(
        string="Target Port", 
        required=True, 
        default="5432")
    target_db_name = fields.Char(
        string="Target DB Name", 
        placeholder="anotherdatabasename", 
        required=True)
    target_db_user = fields.Char(
        string="Target DB User", 
        required=True)
    target_db_password = fields.Char(
        string="Target DB Password", 
        required=True)
    
    source_model = fields.Char(
        'ir.model', 
        string="Source Model", 
        required=True)
    active = fields.Boolean(
        string="Active", 
        default=True)
    targe_model = fields.Many2one(
        'ir.model', 
        string="Target Model", 
        required=True)
    
    compactible_field_ids = fields.One2many(
        'ma.import.line', 
        'import_id', 
        string="Compactible Fields"
        )
    # state = fields.Selection(
    #     [
    #         ("draft", "Fixed Annuity"),
    #         ("fixed-principal", "Fixed Principal"),
    #         ("interest", "Only interest"),
    #     ],
    #     related="loan_id.loan_type",
    #     readonly=True,
    # ) 
    
    def connect_source_connection(self):
        sc = psycopg2.connect(
                    dbname=self.source_db_name,
                    user=self.source_db_user,
                    password=self.source_db_password,
                    host=self.source_host,       # or IP address
                    port=self.source_port             # default PostgreSQL port
                )
        return sc
        
    def connect_target_connection(self):
        tc = psycopg2.connect(
                    dbname=self.target_db_name,
                    user=self.target_db_user,
                    password=self.target_db_password,
                    host=self.target_host,       # or IP address
                    port=self.target_port             # default PostgreSQL port
                )
        return tc
        
    def connect_database(self):
        src_connection = self.connect_source_connection()
        trt_connection = self.connect_target_connection()
        return src_connection, trt_connection
        
    def close_connection(self, source_connection, target_connection):
        source_connection.close()
        target_connection.close()
    
    def run_migration(self):
        pass 
       
    def source_table_columns(self):
        """
        Connects to database source -
        Get all the columns and properties
        build compactible field lines
        --- User will now select from each line and mapped 
        --- the target fields to any line that the source field matches 
        """
        table = self.source_model.replace('.','_')
        conn = self.connect_source_connection()
        # Create a cursor
        cursor = conn.cursor()

        # # Example query
        query = f"""
            SELECT
                c.table_name,
                c.column_name,
                c.data_type,
                tc.constraint_type,
                ccu.table_name AS foreign_table,
                ccu.column_name AS foreign_column
            FROM
                information_schema.columns AS c
            LEFT JOIN information_schema.key_column_usage AS kcu
                ON c.table_name = kcu.table_name
                AND c.column_name = kcu.column_name
                AND c.table_schema = kcu.table_schema
            LEFT JOIN information_schema.table_constraints AS tc
                ON tc.constraint_name = kcu.constraint_name
                AND tc.constraint_type = 'FOREIGN KEY'
            LEFT JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
            WHERE
                c.table_name = {table}
                AND c.table_schema = 'public'
            ORDER BY
                c.ordinal_position;
        """
        cursor.execute(query)
        results = cursor.fetchall()
        result = [str(row[0]) for row in results]
        _logger.info(f"""THIS IS THE COLUMNS == > {results} ======= {result}""")
        
        self.generate_compactible_lines(results)
        conn.close()
        
    def generate_compactible_lines(self, results):
        for row in results:
            query = f"""INSERT INTO ma_import_report 
            (import_id, source_column_name, source_field_data_type, source_field_foreign_key) 
            VALUES ({self.id}, {row[2]}, {3}, {5}) RETURNING id;"""
            self.env.cr.execute(query)
            
            