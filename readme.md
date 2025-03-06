#Create this schedule action to update Applicants from Survery, but remember to mdify apprioprately

applicants = env['hr.applicant'].search([('survey_user_input_id', '!=', False)])

for applicant in applicants:
    survey_input = applicant.survey_user_input_id

    if survey_input.survey_id.id == 2:
        lines = survey_input.user_input_line_ids.sorted('question_sequence')

        if len(lines) >= 2:
            vals = {}

            date_of_birth_answer = lines[1].display_name
            if date_of_birth_answer:
                vals['date_of_birth'] = date_of_birth_answer

            gender_answer = lines[0].display_name
            if gender_answer:
                vals['gender'] = gender_answer

            if vals:
                applicant.write(vals)

log(f"Processed {len(applicants)} applicants", level='info')
