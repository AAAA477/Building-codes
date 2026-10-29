import json, os
os.chdir(r"C:\Users\aaaan\Downloads\Building codes\app\data\content")
NBC = "NBC_2023AE_2nd_printing.pdf"
PAB = "11_Edmonton_Point_Access_Block.pdf"
EM = "10_Edmonton_Emergency_Services_Guideline.pdf"
SES = "ma-standata-interpretation-joint-23bci026-23fci014-2026-10.pdf"
BRIEF = "00_Challenge_Scope.pdf"
CAL = "09_Calgary_Alt_Solution_Guide.pdf"
INT = "NBC_2020_Intent_Supplement.pdf"
S = lambda d, p: {"doc": d, "page": p}


def dump(name, obj):
    json.dump(obj, open(name, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(name, "ok")


# ---------------------------------------------------------------- emergency screen
dump("edmonton_emergency_screen.json", {
    "title": "Edmonton emergency-services screen",
    "guideline": "COE-IM-GUIDE-0040 v01 (2025-04-15), Guideline for Alternative Solutions Affecting Emergency Services",
    "purpose": "These questions determine whether a design merits review of its impact on emergency response. They are a screen for the applicant's professional, not a finding about the design.",
    "source": S(EM, 8),
    "lead_in": "There is no clear prescription for determining how an alternative solution may impact the capability and procedures of emergency responders, and the evaluation must be made by a competent designer using good fire protection engineering practices. To aid that assessment, the following questions should be used to determine whether a design merits review of impact to emergency response:",
    "questions": [
        {"id": "ES1", "number": 1, "answer_options": ["yes", "no", "unsure"], "source": S(EM, 8),
         "text": "Does the alternative solution modify any specific firefighting requirement of the NBC(AE), including Division B, Subsection 3.2.5., or other specific firefighting provisions?",
         "sub_points": [
             {"id": "ES1.1", "text": "Variance of any prescriptive firefighting measure in the NBC(AE) indicates that the designer must understand and communicate the operational impact of that Variance.", "source": S(EM, 8)},
             {"id": "ES1.2", "text": "Equally, any variance which includes reference to Functional Statements F06, F12, or F13 likely impact emergency services.", "source": S(EM, 8)}]},
        {"id": "ES2", "number": 2, "answer_options": ["yes", "no", "unsure"], "source": S(EM, 8),
         "text": "Do the life safety or property protection features of the alternative solution design rely on timely intervention by the local fire service, including for spatial separation/exposure protection?",
         "sub_points": [{"id": "ES2.1", "text": "The NBC(AE) generally assumes intervention by a local fire department on the timescale of 10 minutes, to correspond to the need to address exposure protection of adjacent buildings. While only a rough estimate, any alternative solution which impacts this intervention, or more generally an intended/known delay to fire department response, must evaluate the impact of that variance.", "source": S(EM, 8)}]},
        {"id": "ES3", "number": 3, "answer_options": ["yes", "no", "unsure"], "source": S(EM, 8),
         "text": "Does the alternative solution introduce equipment, technology, or processes which are novel to Edmonton Fire Rescue Services, or which may be incompatible with technology and equipment used by responders?",
         "sub_points": [
             {"id": "ES3.1", "text": "Special instructions for responders may be part of an emergency response plan for a building. This can include systems such as automatic smoke control which may impact fire department procedures for ventilation, and which may require specific pre-incident training or familiarization.", "source": S(EM, 8)},
             {"id": "ES3.2", "text": "Adherence to specific emergency response actions by EFRS as part of an alternative solution building design, or utilization of equipment which is not otherwise prescribed/regulated in Division B of the NBC(AE) indicates an impact to responders.", "source": S(EM, 8)}]},
        {"id": "ES4", "number": 4, "answer_options": ["yes", "no", "unsure"], "source": S(EM, 8),
         "text": "Does the alternative solution require special operational plans for occupants which may affect emergency response and intervention?",
         "sub_points": [
             {"id": "ES4.1", "text": "Shelter in place, including areas of refuge, staged evacuations, and bespoke emergency communication/instruction are examples of procedures which are generally required by the National Fire Code, Alberta Edition for Fire Safety Plans. Understanding the impact of these procedures is essential to the alternative solution designer, to ensure assumptions on fire department intervention are properly attributed.", "source": S(EM, 9)},
             {"id": "ES4.2", "text": "Strategies which rely on fire department intervention/action or which utilize uncommon occupant evacuation plans indicate a need to assess the impacts to emergency responders.", "source": S(EM, 9)}]}],
    "functional_statement_trigger": {
        "functions": ["F06", "F12", "F13"],
        "rule": "Any variance which includes reference to Functional Statements F06, F12, or F13 likely impacts emergency services.",
        "source": S(EM, 8),
        "function_text": {"F06": "To retard the effects of fire on facilities for notification, suppression and emergency response.", "F12": "To facilitate emergency response.", "F13": "To notify emergency responders, in a timely manner, of the need to take action in an emergency."},
        "function_text_source": S(NBC, 80),
        "single_exit_stair_prefill": "NBC(AE) 3.4.2.1.(1), the minimum-number-of-exits sentence a single exit stair varies, is attributed F12 and F06 (NBC(AE) 2023 Table 3.10.1.1, p.346). The trigger in question ES1.2 is therefore expected to be met; the applicant's professional must still confirm.",
        "prefill_source": S(NBC, 346)},
    "response_time_boundary": {
        "text": "The NBC(AE) generally assumes fire department intervention on the timescale of 10 minutes. EFRS service-level targets give a typical first-unit arrival within 7 minutes and a first alarm assignment of at least 16 firefighters within 11 minutes of receipt of an emergency call. Exceptions are identified by the Outside 10-minute Boundary map published on maps.edmonton.ca (layer 'ERD Public Data'). For projects outside this response area, careful consideration must be given both to the impact to spatial separation as defined in the NBC(AE), and to the impact of delayed emergency response.",
        "intake_question": "Is the site outside the Edmonton 10-minute response boundary (map layer 'ERD Public Data' on maps.edmonton.ca)?",
        "source": S(EM, 15), "supporting_source": S(EM, 8)},
    "outcome_rules": [
        {"if": "any question answered yes or unsure, or the F06/F12/F13 trigger is met", "then": "Flag 'emergency services impact must be evaluated by the responsible professional'. Do not draft the evaluation. Add the Section D item 'Emergency services impact assessment'.", "source": S(EM, 9)},
        {"if": "all answers no and no F06/F12/F13 reference", "then": "No additional emergency-services analysis is required by this guideline (alternative solutions that show no additional or unique impacts relative to the acceptable solutions do not require it), but the professional must confirm.", "source": S(EM, 3)}],
    "disclaimer": "The guideline is not design or code advice; professionals remain responsible for verifying details (p.23). This tool screens for completeness only.",
    "disclaimer_source": S(EM, 23),
    "contact_note": "For an in-progress permit application contact the assigned plans examiner (p.23).",
    "documentation_prompts": [
        {"id": "ES-DOC1", "text": "Document assumptions and limiting or restricting factors associated with emergency response that is affected by the alternative solution.", "source": S(EM, 20)},
        {"id": "ES-DOC2", "text": "Demonstrate performance objectively relative to the Division B acceptable solutions; conclusions of 'approximately equal or better' must not rest on judgement without demonstration.", "source": S(EM, 21)},
        {"id": "ES-DOC3", "text": "Identify all fire and life safety systems needing inspection, testing and maintenance (ITM) not regulated by the NFC(AE); include ITM and commissioning documentation, naming who is accountable, coordinated with the Registered Professional of Record and the Coordinating Registered Professional.", "source": S(EM, 22)}]})

# ---------------------------------------------------------------- professional rules
STOP = "STOP. This is where the tool ends. Preparing the engineering analysis, risk assessment, fire-safety design or equivalence argument for a single exit stair is professional work. In Edmonton it must be done by registered professionals and a qualified Fire Protection or Life Safety Code Consultant. This tool will not write it, and it does not say whether the design is safe or equivalent. Below is what your professional must address. Hand this list to them."
dump("professional_rules.json", {
    "stop_language": {
        "ui_text": STOP,
        "short_text": "Professional required. The tool lists what must be addressed and leaves it blank. It does not judge whether the design is safe, equivalent or acceptable.",
        "export_banner": "Professional required, Section D incomplete. This document checks completeness only, not technical correctness.",
        "basis": "Tool wording written for this product; the requirements it states come from the cited rules.",
        "source": S(PAB, 8)},
    "rules": [
        {"id": "PR1", "topic": "single_exit_stair", "jurisdiction": "edmonton", "stop": True,
         "text": "Professional involvement is required. Registered professional architect and/or engineers are involved in the design and field review of the project, as well as the preparation of the Alternative Solution. Plans and specifications must be properly authenticated and validated, as per the practice standards of the professional organizations.",
         "source": S(PAB, 8), "quote_kind": "paraphrase_minimal"},
        {"id": "PR2", "topic": "single_exit_stair", "jurisdiction": "edmonton", "stop": True,
         "text": "Applications that put forward a Point Access Block are required to submit an Alternative Solution prepared by a qualified Fire Protection or Life Safety Code Consultant.",
         "source": S(PAB, 8), "supporting_source": S(PAB, 4)},
        {"id": "PR3", "topic": "single_exit_stair", "jurisdiction": "edmonton", "stop": True,
         "text": "Professionals should exhibit skills associated with fire protection engineering as described in the Society of Fire Protection Engineers 'Recommended Minimum Technical Core Competencies for the Practice of Fire Protection Engineering'.",
         "source": S(PAB, 4)},
        {"id": "PR4", "topic": "single_exit_stair", "jurisdiction": "edmonton", "stop": True,
         "text": "The Alternative Solution must demonstrate compliance with the NBC(AE) by showing how a Single Egress Stair will perform to an equivalent or enhanced level of resiliency as a development with two egress stairs. Only the professional can make this demonstration; the tool must not.",
         "source": S(PAB, 8)},
        {"id": "PR5", "topic": "any", "jurisdiction": "alberta", "stop": False,
         "text": "Involvement of a registered professional is not required for a residential building that is a single-family dwelling or a multiple-family dwelling that contains 4 dwelling units or less (and other classes listed), except where Sentence 2.4.1.1.(4) applies. For other buildings the drawings and specifications shall be authenticated by one or more registered professionals.",
         "article_refs": ["2.4.1.1"], "source": S(NBC, 739), "supporting_source": S(NBC, 740),
         "tool_action": "If units on the site exceed 4 (for a multiple-family dwelling), set professional_required = true on Section D rows and raise a professional flag."},
        {"id": "PR6", "topic": "any", "jurisdiction": "alberta", "stop": True,
         "text": "If the size or complexity of a project may give rise to special safety concerns, the authority having jurisdiction may require the involvement of one or more registered professionals to authenticate all or part of the drawings and specifications and perform field reviews.",
         "article_refs": ["2.4.1.1"], "source": S(NBC, 740)},
        {"id": "PR7", "topic": "any", "jurisdiction": "alberta", "stop": True,
         "text": "For projects within the scope of Sentence 2.4.1.1.(3), the owner shall, before applying for a permit, retain a coordinating registered professional and registered professionals of record, and provide the authority having jurisdiction with Schedules A and B.",
         "article_refs": ["2.4.2.1", "2.4.2.2"], "source": S(NBC, 741)},
        {"id": "PR8", "topic": "any", "jurisdiction": "alberta", "stop": False,
         "text": "The Code analysis must include information about the qualifications, experience and background of the person or persons taking responsibility for the design; where more than one person takes responsibility for different aspects, the applicant for the permit shall identify a single person to co-ordinate the preparation of the design, Code analysis and documentation.",
         "article_refs": ["2.3.1.1"], "source": S(NBC, 739)},
        {"id": "PR9", "topic": "single_exit_stair", "jurisdiction": "alberta", "stop": False,
         "text": "Provincial position: where compliance is addressed by an alternative solution, the qualification of the person developing it may include a registered professional but is not prescribed as such; Subclause 2.4.1.1.(1)(b)(ii) of Division C requires professional involvement for buildings containing more than 4 dwelling units.",
         "source": S(SES, 2)},
        {"id": "PR10", "topic": "any", "jurisdiction": "alberta", "stop": False,
         "text": "If the work constitutes the practice of engineering or architecture, flag it explicitly. The tool must identify when development or evaluation of the proposal constitutes the practice of Engineering.",
         "source": S(BRIEF, 3)},
        {"id": "PR11", "topic": "any", "jurisdiction": "calgary", "stop": False,
         "text": "If a professional is required for the project or the subject of the variance, the supporting documents must also be stamped and sealed.",
         "source": S(CAL, 3)}],
    "stop_points": [
        {"id": "SP1", "where": "Section D rows for code analysis, risk assessment, testing/studies, ITM/commissioning", "action": "Show the list of required content; leave blank; mark provenance needs_professional.", "rule_ids": ["PR1", "PR2", "PR4"]},
        {"id": "SP2", "where": "Section C explainer paragraphs", "action": "May explain what each article requires in plain words (lookup). Must not state that the alternative is equivalent or safe.", "rule_ids": ["PR4"]},
        {"id": "SP3", "where": "Proposed alternative and mitigations", "action": "Record what the applicant says. Do not generate performance claims, numbers (travel distances, ratings, flow rates) or engineering sizing.", "rule_ids": ["PR4"]},
        {"id": "SP4", "where": "Declarations and signatures", "action": "Never tick on the user's behalf.", "rule_ids": []}],
    "source_conflicts": [
        {"id": "SC1", "text": "The Challenge Scope appendix (00_Challenge_Scope.pdf p.11) quotes '2.4.2.1.(1) Professional Design' as 'Where required, the design and field review shall be carried out by a registered professional skilled in the appropriate discipline.' In NBC(AE) 2023 (2nd printing, p.741) Article 2.4.2.1. is titled 'Application' and says only that the Subsection applies to a project within the scope of Sentence 2.4.1.1.(3). The professional requirements are in 2.4.1.1.(3)-(4) (p.739-740) and 2.4.2.2.-2.4.2.3. (p.741). The tool cites the NBC text.", "source": S(BRIEF, 11), "nbc_source": S(NBC, 741)},
        {"id": "SC2", "text": "The Challenge Scope appendix (p.10-11) also quotes Division A 1.2.1.1.(3), 1.2.1.2.(1), 1.2.1.3.(1) and Division C 2.2.1.2.(1) as article text; these do not match the NBC(AE) 2023 text found in files/codes. Only the 2.3.1.1 text matches. Do not cite them.", "source": S(BRIEF, 10)},
        {"id": "SC3", "text": "Edmonton requires a qualified Fire Protection or Life Safety Code Consultant for a Point Access Block (PAB guide p.8); the provincial STANDATA 23-BCI-026/23-FCI-014 says the qualification of the person developing the alternative solution is not prescribed (p.2). The tool applies the stricter Edmonton rule for an Edmonton application and notes the provincial position.", "source": S(PAB, 8), "other_source": S(SES, 2)}]})

# ---------------------------------------------------------------- section D templates
SDT = lambda i, title, desc, req, ref, src, **k: dict({"id": i, "title": title, "description": desc, "professional_required": req, "code_ref": ref, "source": src}, **k)
dump("section_d_templates.json", {
    "title": "Section D: supporting documentation the application must address",
    "note": "The tool lists what the documentation must address and leaves each item blank. Section D is checked for 'addressed or not', never for adequacy. Completion of the supporting documentation requires professional expertise in most cases (Challenge Scope p.3).",
    "note_source": S(BRIEF, 3),
    "form_columns": "Name of Supporting Documentation and Name of the Individual/Professional and/or Professional Organization Responsible",
    "form_source": S("07_Variance_Form.pdf", 2),
    "items": [
        SDT("SD-01", "Code analysis: methods and rationales", "A Code analysis outlining the analytical methods and rationales used to determine that the proposed alternative solution will achieve at least the level of performance required by Clause 1.2.1.1.(1)(b) of Division A.", True, "NBC Div C 2.3.1.1.(2)(a)", S(NBC, 739), group="code_analysis"),
        SDT("SD-02", "Applicable objectives, functional statements and acceptable solutions", "The Code analysis shall identify the applicable objectives, functional statements and acceptable solutions. The tool pre-fills the Section C attribution table from the verified lookup; the analysis built on it is the professional's.", True, "NBC Div C 2.3.1.1.(3)", S(NBC, 739), group="code_analysis", prefilled_by="section_c lookup"),
        SDT("SD-03", "Assumptions and limiting or restricting factors", "Any assumptions, and limiting or restricting factors, that support the Code compliance assessment.", True, "NBC Div C 2.3.1.1.(3)", S(NBC, 739), group="code_analysis"),
        SDT("SD-04", "Testing procedures, engineering studies, building performance parameters", "Testing procedures, engineering studies or building performance parameters that support the Code compliance assessment.", True, "NBC Div C 2.3.1.1.(3)", S(NBC, 739), group="code_analysis"),
        SDT("SD-05", "Sufficient detail", "Information in sufficient detail to convey the design intent and to support the validity, accuracy, relevance and precision of the Code analysis.", True, "NBC Div C 2.3.1.1.(5)", S(NBC, 739), group="code_analysis"),
        SDT("SD-06", "Special maintenance or operational requirements", "Information concerning any special maintenance or operational requirements necessary for the alternative solution to achieve compliance after the building is constructed.", True, "NBC Div C 2.3.1.1.(2)(b)", S(NBC, 739), group="maintenance_commissioning"),
        SDT("SD-07", "Commissioning requirements", "Any building component commissioning requirements necessary for the alternative solution to achieve compliance after the building is constructed.", True, "NBC Div C 2.3.1.1.(2)(b)", S(NBC, 739), group="maintenance_commissioning"),
        SDT("SD-08", "Inspection, testing and maintenance (ITM) of systems not regulated by the NFC(AE)", "Identify fire and life safety systems introduced by the design that need ITM not otherwise prescribed by the NFC(AE) (for example smoke protection systems); include ITM and commissioning documentation, or state clearly the documentation required and the professional accountable for completing it.", True, "Edmonton Emergency Services Guideline, ITM section", S(EM, 22), group="maintenance_commissioning", jurisdiction="edmonton", also_source=S(EM, 20)),
        SDT("SD-09", "Qualifications, experience and background", "Information about the qualifications, experience and background of the person or persons taking responsibility for the design.", False, "NBC Div C 2.3.1.1.(4)", S(NBC, 739), group="people", note="Supplied by the person taking responsibility; for a Point Access Block that includes the qualified Fire Protection or Life Safety Code Consultant."),
        SDT("SD-10", "Single coordinating person", "Where more than one person takes responsibility for different aspects of the design, the applicant for the permit shall identify a single person to co-ordinate the preparation of the design, Code analysis and documentation.", True, "NBC Div C 2.3.1.1.(6)", S(NBC, 739), group="people", also_source=S(NBC, 741), note="For projects within 2.4.1.1.(3) the owner retains a coordinating registered professional (2.4.2.2.(1)(a), p.741)."),
        SDT("SD-11", "Schedules of professional involvement", "Owner provides the authority having jurisdiction with Schedules A and B before applying for a permit; the coordinating registered professional provides Schedule C-1.", True, "NBC Div C 2.4.2.2.(1)(c), 2.4.2.3.(1)(d)", S(NBC, 741), group="people", applies_when="project falls within 2.4.1.1.(3)"),
        SDT("SD-12", "Alternative Solution prepared by a qualified Fire Protection or Life Safety Code Consultant", "Point Access Block applications must submit an Alternative Solution prepared by a qualified Fire Protection or Life Safety Code Consultant.", True, "Edmonton PAB guide, mandatory criteria", S(PAB, 8), group="single_exit_stair", topic="single_exit_stair", jurisdiction="edmonton", also_source=S(PAB, 4)),
        SDT("SD-13", "Demonstration of equivalent or enhanced resiliency versus two egress stairs", "Show how a Single Egress Stair will perform to an equivalent or enhanced level of resiliency as a development with two egress stairs.", True, "Edmonton PAB guide, mandatory criteria", S(PAB, 8), group="single_exit_stair", topic="single_exit_stair", jurisdiction="edmonton"),
        SDT("SD-14", "Report structure: regulatory framework, problem definition, risk assessment, alternative solutions", "The guide's example Technical Report is organised as Regulatory Framework, Problem Definition, Risk Assessment and Alternative Solutions (mitigations); it is demonstrative and not prescribed.", True, "Edmonton PAB guide, example risk mitigation measures", S(PAB, 5), group="single_exit_stair", topic="single_exit_stair", jurisdiction="edmonton"),
        SDT("SD-15", "Emergency services impact", "Answer the four screening questions; if any is met, document assumptions and limiting factors relating to emergency response and the operational impact of any variance of firefighting provisions.", True, "Edmonton Emergency Services Guideline, Sections 1 and 4", S(EM, 8), group="emergency_services", jurisdiction="edmonton", also_source=S(EM, 20)),
        SDT("SD-16", "Objective demonstration of performance", "Do not rely on subjective assessment. Demonstrate performance relative to the Division B acceptable solutions, or to tenability-based criteria grounded in good engineering practice.", True, "Edmonton Emergency Services Guideline, Subjective Equivalency", S(EM, 20), group="emergency_services", jurisdiction="edmonton", also_source=S(EM, 21)),
        SDT("SD-17", "Retention of documentation on the premises", "After occupancy, documentation conforming to NFC(AE) Article 2.3.1.1. is retained on the premises for review by fire safety codes officers (NFC(AE) Clause 2.3.1.2.(1)(b)); the owner keeps the issued variance documentation available.", False, "STANDATA 23-BCI-026/23-FCI-014; NFC(AE) Div C 2.3.1.2.(1)", S(SES, 7), group="after_approval", topic="single_exit_stair", also_source=S(SES, 2), nfc_source={"doc": "NFC_2023AE.pdf", "page": 351}, responsible="owner"),
        SDT("SD-18", "Pre-application meeting record (recommended)", "Edmonton recommends a pre-application meeting with Development Services for Point Access Block proposals (with Development Planner and Safety Codes officers).", False, "Edmonton PAB guide", S(PAB, 7), group="process", topic="single_exit_stair", jurisdiction="edmonton", optional=True, also_source=S(PAB, 8))]})

# ---------------------------------------------------------------- glossary
dump("glossary.json", {"terms": [
    {"id": "objective", "term": "Objective", "plain": "A goal of the code that explains what harm it tries to prevent, for example fire safety, safety in use or protecting the building from fire. Each code rule in Division B is linked to one or more objectives.",
     "official": "An objective of this Code is to limit the probability that, as a result of the design or construction of the building ... a person in or adjacent to the building will be exposed to an unacceptable risk of injury due to fire. (OS1 Fire Safety)", "official_source": S(NBC, 68), "example": "3.4.2.1.(1) is linked to OS3.7: persons being delayed in or impeded from moving to a safe place during an emergency.", "example_source": S(NBC, 346), "source": S(NBC, 68), "kind": "plain_with_quote"},
    {"id": "functional_statement", "term": "Functional statement", "plain": "A short statement of the job a part of the building has to do, for example to facilitate the timely movement of persons to a safe place in an emergency. A code rule is linked to both objectives and functional statements.",
     "official": "F10: To facilitate the timely movement of persons to a safe place in an emergency. F12: To facilitate emergency response.", "official_source": S(NBC, 80), "source": S(NBC, 80), "kind": "plain_with_quote"},
    {"id": "intent_statement", "term": "Intent statement", "plain": "An explanation published by the code writers of why a rule exists. Intent statements help you understand what an alternative has to achieve. They are explanatory and are not part of the code.",
     "official": "Intent statements serve explanatory purposes only and do not form an integral part of the Codes. They contain useful information that helps Code users understand the rationale behind requirements. This contributes to a more accurate interpretation and application of acceptable solutions and a clearer understanding of what alternative solutions should achieve.",
     "official_source": S(INT, 2), "source": S(INT, 2), "kind": "plain_with_quote", "edition_caveat": "The supplied intent statements are for NBC 2020; the attributions for the articles used here match NBC(AE) 2023."},
    {"id": "acceptable_solution", "term": "Acceptable solution", "plain": "The ready-made rules in Division B (Parts 3 to 11). If you follow them, the code treats you as meeting the linked objectives and functional statements.",
     "official": "Clause (a) makes it clear that the acceptable solutions in Division B are automatically deemed to satisfy the linked objectives and functional statements of Division A.", "official_source": S(NBC, 12), "also_source": S(NBC, 38), "source": S(NBC, 12), "kind": "plain_with_quote"},
    {"id": "alternative_solution", "term": "Alternative solution", "plain": "A different way of building that is not in the acceptable solutions, accepted only if it performs at least as well in the areas the objectives and functional statements cover. It is not a lower standard.",
     "official": "using alternative solutions that will achieve at least the minimum level of performance required by Division B in the areas defined by the objectives and functional statements attributed to the applicable acceptable solutions (Division A, Clause 1.2.1.1.(1)(b)).", "official_source": S(NBC, 38), "source": S(NBC, 38), "kind": "plain_with_quote",
     "note": "'Alternative solution' is not among the italicised defined terms found in the NBC(AE) text used here; the meaning comes from 1.2.1.1.(1)(b). The Challenge Scope appendix quotes a Division A 1.4.1.2. definition that was not found in the NBC(AE) text."},
    {"id": "variance", "term": "Variance", "plain": "Alberta's legal name for an alternative solution. A safety codes officer (or Administrator) issues it in writing, sometimes with conditions, if it gives approximately equivalent or greater safety performance.",
     "official": "In Alberta, the Safety Codes Act recognizes 'alternative solutions' as Variances.", "official_source": S(NBC, 12), "also_source": S(SES, 3), "source": S(NBC, 12), "kind": "plain_with_quote"},
    {"id": "ahj", "term": "Authority having jurisdiction (AHJ)", "plain": "The safety codes officer who reviews your application and decides whether to issue the variance. In Edmonton this is the City's Safety Codes, Permits and Inspections.",
     "official": "Authority having jurisdiction means a safety codes officer in the building discipline exercising authority pursuant to designation of powers and terms of employment in accordance with the Safety Codes Act.", "official_source": S(NBC, 42), "source": S(NBC, 42), "kind": "plain_with_quote"},
    {"id": "registered_professional", "term": "Registered professional", "plain": "A registered architect, registered engineer or licensed interior designer. Some projects must have one involved; the single exit stair in Edmonton needs more (see professional rules).",
     "official": "Registered professional means an individual who qualifies as a (a) registered architectural professional, (b) registered engineering professional, or (c) licensed interior designer.", "official_source": S(NBC, 50), "source": S(NBC, 50), "kind": "plain_with_quote"},
    {"id": "exit", "term": "Exit", "plain": "The part of the escape route that leads from a floor out to the outside or to a protected outdoor space, such as an enclosed exit stair.",
     "official": "Exit means that part of a means of egress, including doorways, that leads from the floor area it serves to a separate building, an open public thoroughfare, or an exterior open space protected from fire exposure from the building and having access to an open public thoroughfare.", "official_source": S(NBC, 44), "also_source": S(SES, 4), "source": S(NBC, 44), "kind": "plain_with_quote"},
    {"id": "point_access_block", "term": "Point Access Block (single exit stair building)", "plain": "A compact apartment building with a limited number of homes clustered around one exit stair.",
     "official": "Point Access Blocks, also known as buildings with Single Egress Stairs (SES), are compact multi-family residential buildings with a limited number of dwelling units clustered around one exit stair.", "official_source": S(PAB, 2), "source": S(PAB, 2), "kind": "plain_with_quote"}],
    "note": "Plain-language wording is written for this tool; official wording is quoted from the cited page. NBC(AE) 2023 2nd printing."})

# ---------------------------------------------------------------- stair module
dump("stair_module.json", {
    "id": "single_exit_stair", "title": "Single exit stair (Point Access Block)", "jurisdiction_overlay": "edmonton",
    "edition": "NBC(AE) 2023 (2nd printing)",
    "scope": {
        "in_scope": [
            {"text": "Residential buildings of 6 storeys or less with not more than 4 units per floor served by a single egress stair.", "source": S(PAB, 2)},
            {"text": "Alternative Solution varying the number of exits required in a building, or any other aspect that does not adhere to the acceptable solutions.", "source": S(PAB, 4)},
            {"text": "Part 3 or Part 9 buildings: professional involvement is expected 'whether they fall under Part 9 or Part 3 of the building code relative to scale and occupancy'.", "source": S(PAB, 2)}],
        "out_of_scope": [
            {"text": "Non-residential occupancies, buildings over 6 storeys, or more than 4 units per floor: outside the stated scope of the Edmonton guide. Show the general checklist and recommend a pre-application meeting; no Edmonton PAB-specific guidance is available.", "source": S(PAB, 2), "status": "derived from the guide's stated scope; the guide does not itself say these are prohibited"},
            {"text": "The guide's analysis is an example and contemplates only this specific variance.", "source": S(PAB, 4)},
            {"text": "'High Buildings' (NBC(AE) Division B Subsection 3.2.6.) are outside the scope of the Edmonton emergency-services guideline; contact its authors.", "source": S(EM, 4)}],
        "existing_variance_check": {
            "text": "Provincial interpretation STANDATA 23-BCI-026/23-FCI-014 (October 2026) confirms an AHJ may accept a residential single-egress-stair building via an alternative solution when the documentation conforms to Division C Section 2.3 and the design provides approximately equivalent or greater safety performance in the areas defined by the objectives and functional statements of the applicable acceptable solutions. No STANDATA variance granting a blanket single-stair permission was found in files/standata.",
            "source": S(SES, 7), "standata_number": "23-BCI-026/23-FCI-014"},
        "pre_application_meeting": {"text": "Recommended before submission; includes a Development Planner and Safety Codes officers.", "source": S(PAB, 7)}},
    "topic_questions": [
        {"id": "st1", "prompt": "How many storeys is the building?", "help": "Count floors above ground. The Edmonton guide covers 6 storeys or less.", "field_path": "project.storeys", "type": "number", "required": True, "source": S(PAB, 2), "scope_check": "<=6"},
        {"id": "st2", "prompt": "How many dwelling units are on each floor served by the stair?", "help": "The Edmonton guide covers not more than 4 units per floor.", "field_path": "project.units_per_floor", "type": "number", "required": True, "source": S(PAB, 2), "scope_check": "<=4"},
        {"id": "st3", "prompt": "Is the building sprinklered throughout?", "help": "Sprinklered status changes which exception, if any, of Article 3.4.2.1. could apply and is a basic fact the professional needs.", "field_path": "project.sprinklered", "type": "bool", "required": True, "source": S(NBC, 269)},
        {"id": "st4", "prompt": "What is the longest travel distance from a dwelling unit door to the exit stair, if known?", "help": "Measured along the path you would walk. Leave blank if the designer has not measured it yet; the professional must supply it. The tool does not calculate or judge it.", "field_path": "variance.stair.travel_distance_m", "type": "number", "required": False, "source": S(NBC, 271), "note": "Travel distance is addressed by 3.4.2.4. (p.271)"},
        {"id": "st5", "prompt": "Describe how the stair is enclosed and separated from the rest of the building.", "help": "For example the type of walls, doors and openings around the stair. Say what the plans show; do not claim it is adequate.", "field_path": "variance.stair.enclosure_description", "type": "text", "required": False, "source": S(PAB, 5), "note": "Compartmentation is a main component identified in the guide's example assessment."},
        {"id": "st6", "prompt": "Describe any smoke control or smoke management provided for the stair.", "help": "For example mechanical or passive measures to keep smoke out of the stair. If none, say none.", "field_path": "variance.stair.smoke_management_description", "type": "text", "required": False, "source": S(PAB, 5)},
        {"id": "st7", "prompt": "Describe fire department access to the building and the stair.", "help": "Access routes and access to the building and roof; any difference from the code's firefighting provisions (Subsection 3.2.5.).", "field_path": "variance.stair.fire_department_access_description", "type": "text", "required": False, "source": S(EM, 11)},
        {"id": "st8", "prompt": "Is the site outside the Edmonton 10-minute response boundary?", "help": "Check the 'Outside 10-minute Boundary' map layer on maps.edmonton.ca. If outside, the professional must consider delayed response.", "field_path": "variance.stair.outside_10_minute_boundary", "type": "bool", "required": False, "source": S(EM, 15)},
        {"id": "st9", "prompt": "Does the design rely on any special occupant plans (shelter in place, staged evacuation, refuge areas)?", "help": "Such plans affect the emergency-services screen.", "field_path": "variance.stair.occupant_plans", "type": "text", "required": False, "source": S(EM, 8)}],
    "benchmark_acceptable_solution": {
        "articles": ["3.4.2.1.(1)"],
        "plain_words": "Every floor area intended for occupancy must be served by at least 2 exits, except where Sentences (2) to (4) permit otherwise. The words of Sentence 3.4.2.1.(1) are: 'Except as permitted by Sentences (2) to (4), every floor area intended for occupancy shall be served by at least 2 exits.'",
        "exceptions": [
            {"sentence": "3.4.2.1.(2)", "text": "A floor area in a building not more than 2 storeys in building height may be served by one exit if the total occupant load served by the exit is not more than 60 and the floor area and travel distance are within Table 3.4.2.1.-A (not sprinklered throughout), or, if sprinklered throughout, travel distance is not more than 25 m and floor area is within Table 3.4.2.1.-B.", "source": S(NBC, 269), "supporting_source": S(NBC, 270)},
            {"sentence": "3.4.2.1.(4)", "text": "Sentences (1) and (2) may be waived for dwelling units that have an access to exit conforming to Sentences 3.3.4.4.(1) to (4).", "source": S(NBC, 270)}],
        "why_it_matters": "A building taller than the exceptions allow, with one exit stair, does not comply with the acceptable solution. The Edmonton guide states Point Access Blocks over two storeys can only be constructed through an accepted Alternative Solution.",
        "why_source": S(PAB, 2),
        "attributions": {"3.4.2.1.(1)": ["F10-OS3.7", "F12-OS3.7", "F05-OS3.7", "F06-OS3.7", "F12-OS1.2", "F06-OS1.2", "F12-OP1.2", "F06-OP1.2"]},
        "attribution_source": S(NBC, 346),
        "related_articles": [
            {"article": "3.4.2.3.(1)", "reason": "Distance between two exits", "source": S(NBC, 271)},
            {"article": "3.4.2.4.", "reason": "Travel distance to an exit", "source": S(NBC, 271)},
            {"article": "3.4.4.1.(1)", "reason": "Fire-resistance rating of exit separations (the stair enclosure)", "source": S(NBC, 274)},
            {"article": "3.2.5.1.", "reason": "Access to above-grade storeys for firefighting", "source": S(NBC, 228)}],
        "part_9_counterpart": {"article": "9.9.8.2.(1)", "text": "At least 2 exits shall be provided from every floor area, with maximum travel distances; single exit permitted from each storey in buildings of 1 and 2 storeys under Sentence (2).", "source": S(NBC, 871), "objective_function_attribution": "unresolved: not looked up for this module"},
        "verification": "Article existence is checked against the NBC(AE) 2023 2nd printing text by the validation script."},
    "mitigation_catalogue": {
        "note": "Items come only from the Edmonton PAB guide and the Edmonton emergency-services guideline. The guide's technical report with measures and 13 design studies is not in files/, so the catalogue does not list technical performance values and the tool does not say whether any measure is sufficient.",
        "items": [
            {"id": "MIT-COMP", "label": "Compartmentation", "plain": "Fire separations and enclosure around the stair so that fire and smoke do not compromise it.", "source": S(PAB, 5), "basis": "The exemplar assessment identifies the main components that could lead to stair failure as relating to compartmentation and smoke management and outlines respective risk mitigation measures.", "evidence_prompt": "Which drawings or reports describe the stair enclosure and separations?", "related_article": "3.4.4.1.(1)", "professional_required": True},
            {"id": "MIT-SMOKE", "label": "Smoke management", "plain": "Measures that limit smoke getting into or spreading within the stair.", "source": S(PAB, 5), "basis": "As above. If automatic smoke control is used, the emergency-services guideline notes it may impact fire department ventilation procedures and may require pre-incident training or familiarization.", "also_source": S(EM, 8), "evidence_prompt": "Which design report describes the smoke management?", "professional_required": True},
            {"id": "MIT-RESPONSE", "label": "Emergency response considerations (access and response time)", "plain": "Showing how firefighters get to and into the building and how the design relates to the 10-minute assumption, and to Edmonton Fire Rescue response information.", "source": S(EM, 8), "also_source": S(EM, 15), "basis": "Screening questions on firefighting provisions and reliance on timely intervention.", "evidence_prompt": "Is the site inside the Edmonton 10-minute response boundary? Is any Subsection 3.2.5. provision varied?", "professional_required": True},
            {"id": "MIT-PLAN", "label": "Occupant and emergency response plan", "plain": "Special occupant procedures (shelter in place, areas of refuge, staged evacuation, bespoke communication) and how they are assumed to interact with fire department action.", "source": S(EM, 9), "basis": "Procedures generally required by the NFC(AE) for Fire Safety Plans; their impact must be understood so assumptions on fire department intervention are properly attributed.", "evidence_prompt": "Is there a draft fire safety plan or emergency response plan?", "professional_required": True},
            {"id": "MIT-ITM", "label": "Inspection, testing, maintenance and commissioning documentation", "plain": "A plan for checking and maintaining the extra safety systems over the life of the building, including any system the NFC does not regulate.", "source": S(EM, 22), "basis": "ITM documentation including commissioning is required to be provided with the documentation of an alternative solution; coordinate with the Registered Professional of Record and the Coordinating Registered Professional.", "also_source": S(NBC, 739), "evidence_prompt": "Who will write the ITM and commissioning plan and when?", "professional_required": True}],
        "not_catalogued": "Measures such as sprinklers, pressurisation or specific ratings are not listed because the supplied guides do not name them as Point Access Block mitigations (the technical report is not in files/). The applicant may enter their own; they are recorded as applicant-stated and are not endorsed."},
    "process": [
        {"step": "Book a pre-application meeting (recommended)", "source": S(PAB, 7)},
        {"step": "Engage registered professionals and a qualified Fire Protection or Life Safety Code Consultant", "source": S(PAB, 8)},
        {"step": "Screen against the four emergency-services questions", "source": S(EM, 8)},
        {"step": "Submit the Alternative Solution with the building permit application; AHJ and EFRS peer review applies", "source": S(PAB, 6)}],
    "authority_notes": [
        {"text": "A building SCO may refuse a variance for reasons that include insufficient or incomplete information, incorrect input parameters or assumptions, intent not demonstrated, or an unclear or impractical recommendation. A refusal can be appealed to the Safety Codes Council within 30 days.", "source": S(SES, 1), "also_source": S(SES, 2)}]})
