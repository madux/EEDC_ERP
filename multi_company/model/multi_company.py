from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging


_logger = logging.getLogger(__name__)

class Hrregion(models.Model):
    _inherit = "hr.region"
    _description = "hr.region model for multi-company"

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )

class Documentrequestline(models.Model):
    _inherit = "document.request.line"
    _description = "document.request.line model for multi-company"

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )

class Goalsettingsectionline(models.Model):
    _inherit = "goal.setting.section.line"
    _description = "goal.setting.section.line model for multi-company"

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )

class Hracademic(models.Model):
    _inherit = "hr.academic"
    _description = "hr.academic model for multi-company"

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )

class Reslga(models.Model):
    _inherit = "res.lga"
    _description = "res.lga model for multi-company"

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )

class Currentassessmentsectionline(models.Model):
    _inherit = "current.assessment.section.line"
    _description = "current.assessment.section.line model for multi-company"

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )

# class Jobdescriptions(models.Model):
#     _inherit = "job.descriptions"
#     _description = "job.descriptions model for multi-company"

#     company_id = fields.Many2one(
#         'res.company',
#         string="Company",
#         default=lambda self: self.env.user.company_id.id
#     )

class Complaintresolution(models.Model):
    _inherit = "complaint.resolution"
    _description = "complaint.resolution model for multi-company"

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )

# class Descriptionsections(models.Model):
#     _inherit = "description.sections"
#     _description = "description.sections model for multi-company"

#     company_id = fields.Many2one(
#         'res.company',
#         string="Company",
#         default=lambda self: self.env.user.company_id.id
#     )

class Memotype(models.Model):
    _inherit = "memo.type"
    _description = "memo.type model for multi-company"

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )

class Docmgtconfig(models.Model):
    _inherit = "doc.mgt.config"
    _description = "doc.mgt.config model for multi-company"

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )

class Transformer(models.Model):
    _inherit = "transformer"
    _description = "transformer model for multi-company"

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )

class Cbtquestionline(models.Model):
    _inherit = "cbt.question.line"
    _description = "cbt.question.line model for multi-company"

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )

class Pmssection(models.Model):
    _inherit = "pms.section"
    _description = "pms.section model for multi-company"

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )

class Lcsectionline(models.Model):
    _inherit = "lc.section.line"
    _description = "lc.section.line model for multi-company"

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )

class Krasectionline(models.Model):
    _inherit = "kra.section.line"
    _description = "kra.section.line model for multi-company"

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )

class Memocategory(models.Model):
    _inherit = "memo.category"
    _description = "memo.category model for multi-company"

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )

class Memosubstage(models.Model):
    _inherit = "memo.sub.stage"
    _description = "memo.sub.stage model for multi-company"

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )

class Cbttemplateconfig(models.Model):
    _inherit = "cbt.template.config"
    _description = "cbt.template.config model for multi-company"

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )

class Memoback(models.Model):
    _inherit = "memo.back"
    _description = "memo.back model for multi-company"

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )

class Auditloglogline(models.Model):
    _inherit = "auditlog.log.line"
    _description = "auditlog.log.line model for multi-company"

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )

class Trainingsectionline(models.Model):
    _inherit = "training.section.line"
    _description = "training.section.line model for multi-company"

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )

class Cbtanswerlineoption(models.Model):
    _inherit = "cbt.answer.line.option"
    _description = "cbt.answer.line.option model for multi-company"

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )

class Injectionsubstation(models.Model):
    _inherit = "injection.substation"
    _description = "injection.substation model for multi-company"

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )

class Employeesimport(models.Model):
    _inherit = "employees.import"
    _description = "employees.import model for multi-company"

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )

class Qualitychecksectionline(models.Model):
    _inherit = "qualitycheck.section.line"
    _description = "qualitycheck.section.line model for multi-company"

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )

class Pmssectionline(models.Model):
    _inherit = "pms.section.line"
    _description = "pms.section.line model for multi-company"

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )

class Hrrank(models.Model):
    _inherit = "hr.rank"
    _description = "hr.rank model for multi-company"

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )

# class Assessmentdescription(models.Model):
#     _inherit = "assessment.description"
#     _description = "assessment.description model for multi-company"

#     company_id = fields.Many2one(
#         'res.company',
#         string="Company",
#         default=lambda self: self.env.user.company_id.id
#     )

# class Pmsdepartmentsectionline(models.Model):
#     _inherit = "pms.department.section.line"
#     _description = "pms.department.section.line model for multi-company"

#     company_id = fields.Many2one(
#         'res.company',
#         string="Company",
#         default=lambda self: self.env.user.company_id.id
#     )

class Scoresheetexport(models.Model):
    _inherit = "score.sheet.export"
    _description = "score.sheet.export model for multi-company"

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )

class Signrequest(models.Model):
    _inherit = "sign.request"
    _description = "sign.request model for multi-company"

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )

class Memoconfig(models.Model):
    _inherit = "memo.config"
    _description = "memo.config model for multi-company"

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )

class Hremployeetransfer(models.Model):
    _inherit = "hr.employee.transfer"
    _description = "hr.employee.transfer model for multi-company"

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )

class Memofleetmaintenance(models.Model):
    _inherit = "memo.fleet.maintenance"
    _description = "memo.fleet.maintenance model for multi-company"

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )

class Skillproficiencyscale(models.Model):
    _inherit = "skill.proficiency.scale"
    _description = "skill.proficiency.scale model for multi-company"

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )

class Memostage(models.Model):
    _inherit = "memo.stage"
    _description = "memo.stage model for multi-company"

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )

class Pmsinstruction(models.Model):
    _inherit = "pms.instruction"
    _description = "pms.instruction model for multi-company"

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )

class Transformerdistrict(models.Model):
    _inherit = "transformer.district"
    _description = "transformer.district model for multi-company"

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )

class Auditlogrule(models.Model):
    _inherit = "auditlog.rule"
    _description = "auditlog.rule model for multi-company"

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )

class Hrjob(models.Model):
    _inherit = "hr.job"
    _description = "hr.job model for multi-company"

    # company_id = fields.Many2one(
    #     'res.company',
    #     string="Company",
    #     default=lambda self: self.env.user.company_id.id
    # )

class Auditloglog(models.Model):
    _inherit = "auditlog.log"
    _description = "auditlog.log model for multi-company"

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )

class Auditloghttpsession(models.Model):
    _inherit = "auditlog.http.session"
    _description = "auditlog.http.session model for multi-company"

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )

class Issuestage(models.Model):
    _inherit = "issue.stage"
    _description = "issue.stage model for multi-company"

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )

class Hrworkunit(models.Model):
    _inherit = "hr.work.unit"
    _description = "hr.work.unit model for multi-company"

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )

class Surveysurvey(models.Model):
    _inherit = "survey.survey"
    _description = "survey.survey model for multi-company"

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )

class Hrcertification(models.Model):
    _inherit = "hr.certification"
    _description = "hr.certification model for multi-company"

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )

class Pmsdepartmentsection(models.Model):
    _inherit = "pms.department.section"
    _description = "pms.department.section model for multi-company"

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )

class Hrapplicantdocumentation(models.Model):
    _inherit = "hr.applicant.documentation"
    _description = "hr.applicant.documentation model for multi-company"

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )

class Memofleet(models.Model):
    _inherit = "memo.fleet"
    _description = "memo.fleet model for multi-company"

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )

class Pmscategory(models.Model):
    _inherit = "pms.category"
    _description = "pms.category model for multi-company"

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )

class Hrlevelcategory(models.Model):
    _inherit = "hr.level.category"
    _description = "hr.level.category model for multi-company"

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )

class Pmsyear(models.Model):
    _inherit = "pms.year"
    _description = "pms.year model for multi-company"

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )

# class Hrjobrecruitmentrequest(models.Model):
#     _inherit = "hr.job.recruitment.request"
#     _description = "hr.job.recruitment.request model for multi-company"

#     company_id = fields.Many2one(
#         'res.company',
#         string="Company",
#         default=lambda self: self.env.user.company_id.id
#     )

class Dsmchecklist(models.Model):
    _inherit = "dsm.checklist"
    _description = "dsm.checklist model for multi-company"

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )

class Failedtransformerissue(models.Model):
    _inherit = "failed.transformer.issue"
    _description = "failed.transformer.issue model for multi-company"

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )

class Hrcontractwizard(models.Model):
    _inherit = "hr.contract.wizard"
    _description = "hr.contract.wizard model for multi-company"

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )

class Hrlevel(models.Model):
    _inherit = "hr.level"
    _description = "hr.level model for multi-company"

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )

class Hrunit(models.Model):
    _inherit = "hr.unit"
    _description = "hr.unit model for multi-company"

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )

class Kbadescriptions(models.Model):
    _inherit = "kba.descriptions"
    _description = "kba.descriptions model for multi-company"

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )

class Helpdesksla(models.Model):
    _inherit = "helpdesk.sla"
    _description = "helpdesk.sla model for multi-company"

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )

class Fcsectionline(models.Model):
    _inherit = "fc.section.line"
    _description = "fc.section.line model for multi-company"

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )

class Memostageinvoiceline(models.Model):
    _inherit = "memo.stage.invoice.line"
    _description = "memo.stage.invoice.line model for multi-company"

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )

class Auditlogloglineview(models.Model):
    _inherit = "auditlog.log.line.view"
    _description = "auditlog.log.line.view model for multi-company"

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )

class Hrgrade(models.Model):
    _inherit = "hr.grade"
    _description = "hr.grade model for multi-company"

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )

class Pmsdepartment(models.Model):
    _inherit = "pms.department"
    _description = "pms.department model for multi-company"

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )

class Multibranch(models.Model):
    _inherit = "multi.branch"
    _description = "multi.branch model for multi-company"

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )

class Memomodel(models.Model):
    _inherit = "memo.model"
    _description = "memo.model model for multi-company"

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )

class Potentialassessmentsectionline(models.Model):
    _inherit = "potential.assessment.section.line"
    _description = "potential.assessment.section.line model for multi-company"

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )

class Auditloghttprequest(models.Model):
    _inherit = "auditlog.http.request"
    _description = "auditlog.http.request model for multi-company"

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )

class Requestline(models.Model):
    _inherit = "request.line"
    _description = "request.line model for multi-company"

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )

class Hremployeetransferline(models.Model):
    _inherit = "hr.employee.transfer.line"
    _description = "hr.employee.transfer.line model for multi-company"

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )

class Surveyuser_input(models.Model):
    _inherit = "survey.user_input"
    _description = "survey.user_input model for multi-company"

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )

class Documentationtype(models.Model):
    _inherit = "documentation.type"
    _description = "documentation.type model for multi-company"

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )

class Hrleave(models.Model):
    _inherit = "hr.leave"
    _description = "hr.leave model for multi-company"

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )

class Hrrecruitmentstage(models.Model):
    _inherit = "hr.recruitment.stage"
    _description = "hr.recruitment.stage model for multi-company"

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )

class Documentsfolder(models.Model):
    _inherit = "documents.folder"
    _description = "documents.folder model for multi-company"

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )

class Pmsappraisee(models.Model):
    _inherit = "pms.appraisee"
    _description = "pms.appraisee model for multi-company"

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )

class Hrdistrict(models.Model):
    _inherit = "hr.district"
    _description = "hr.district model for multi-company"

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )

class Memostagedocumentline(models.Model):
    _inherit = "memo.stage.document.line"
    _description = "memo.stage.document.line model for multi-company"

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )

class Irattachment(models.Model):
    _inherit = "ir.attachment"
    _description = "ir.attachment model for multi-company"

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )

# class Hrapplicant(models.Model):
#     _inherit = "hr.applicant"
#     _description = "hr.applicant model for multi-company"

#     company_id = fields.Many2one(
#         'res.company',
#         string="Company",
#         default=lambda self: self.env.user.company_id.id
#     )

class Hrexperience(models.Model):
    _inherit = "hr.experience"
    _description = "hr.experience model for multi-company"

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )

class Hyrkrasectionline(models.Model):
    _inherit = "hyr.kra.section.line"
    _description = "hyr.kra.section.line model for multi-company"

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )

class Failedtransformermovement(models.Model):
    _inherit = "failed.transformer.movement"
    _description = "failed.transformer.movement model for multi-company"

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )