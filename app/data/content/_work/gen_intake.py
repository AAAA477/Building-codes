import json
F1={"doc":"07_Variance_Form.pdf","page":1}
F2={"doc":"07_Variance_Form.pdf","page":2}
PAB2={"doc":"11_Edmonton_Point_Access_Block.pdf","page":2}
PAB4={"doc":"11_Edmonton_Point_Access_Block.pdf","page":4}
PAB8={"doc":"11_Edmonton_Point_Access_Block.pdf","page":8}
PAB7={"doc":"11_Edmonton_Point_Access_Block.pdf","page":7}
EM8={"doc":"10_Edmonton_Emergency_Services_Guideline.pdf","page":8}
EM22={"doc":"10_Edmonton_Emergency_Services_Guideline.pdf","page":22}
CAL={"doc":"09_Calgary_Alt_Solution_Guide.pdf","page":3}
def q(i,s,p,h,f,t,req=True,src=F1,ch=None,when=None):
    d={"id":i,"section":s,"prompt":p,"help":h,"field_path":f,"type":t,"required":req,"source":src}
    if ch: d["choices"]=ch
    if when: d["when"]=when
    return d
Q=[
q("a1","A","What is the owner's full name?","The legal owner of the property or building (a person or a company). This is the party who will sign the form.","applicant.owner_name","text"),
q("a2","A","Is someone acting for the owner (an architect, engineer, contractor or consultant)? If so, who?","The form has a separate field for the owner's representative. Leave blank if the owner is applying directly.","applicant.owner_representative","text",False,F1),
q("a3","A","What mailing address and email should the Safety Codes Officer use to reach you?","Used for requests for more information and for the decision. Give a full mailing address and one monitored email.","applicant.mailing_address","text"),
q("a3b","A","Email address for correspondence","One email address that is checked regularly.","applicant.email","text",True,CAL),
q("a4","A","What date are you submitting this request?","Today's date unless you plan to submit later.","applicant.date_of_request","date"),
q("b1","B","Which municipality or authority is reviewing the building permit?","This sets the local overlay (form recipient, local guides). The demonstration topic is built around Edmonton.","jurisdiction","choice",True,CAL,["scc","calgary","edmonton"]),
q("b2","B","Is this request for a whole jurisdiction instead of one site?","Tick yes only if the variance is not tied to a single property. Most project variances are site-specific, so answer no.","location.jurisdiction_wide","bool",True,F1),
q("b3","B","What is the building permit number (if you have one yet)?","A variance must be tied to a building permit. If you have not applied yet, leave this blank and say so; Calgary states a variance number cannot be issued without a building permit number.","location.permit_number","text",False,CAL),
q("b4","B","What is the municipal (street) address of the site?","The full street address as it appears on the building permit.","location.municipal_address","text"),
q("b5","B","Do you have the legal land description (lot, block, plan)?","Found on the land title or tax notice. Lot, block and plan describe a city lot.","location.lot","text",False,F1),
q("b5b","B","Block and plan numbers","Block and plan from the land title.","location.block","text",False,F1),
q("b5c","B","Plan number","The registered plan number from the land title.","location.plan","text",False,F1),
q("b6","B","Do you have the Alberta Township Survey (ATS) description (quarter, section, township, range, meridian)?","Mostly used for rural land. Leave blank for a city lot with lot, block and plan.","location.qtr","text",False,F1),
q("b6b","B","Section, township, range, meridian","Enter the section, township, range and meridian from the ATS description (fill each if known).","location.sec","text",False,F1),
q("c1","C","In your own words, what do you want to build or do differently?","Describe the project in a few sentences, for example: a six-storey apartment building with one exit stair.","project.description","text",True,F1),
q("c2","C","What is the building used for (occupancy)?","For example apartments or condominiums (residential), offices, shops. Apartments are the residential occupancy.","project.occupancy","text",True,PAB2),
q("c3","C","How many storeys is the building (building height)?","Count the floors above ground. The Edmonton guide covers residential buildings of 6 storeys or less.","project.storeys","number",True,PAB2),
q("c4","C","What is the building area in square metres?","The footprint area of the largest floor, from your drawings.","project.building_area_m2","number",True,F1),
q("c5","C","How many dwelling units are on each floor?","The Edmonton guide covers not more than 4 units per floor served by one exit stair.","project.units_per_floor","number",True,PAB2),
q("c6","C","Is the building sprinklered throughout?","Fully sprinklered means automatic sprinklers in the whole building. Answer unknown if not decided.","project.sprinklered","bool",True,PAB4),
q("c7","C","Is this a new building or a renovation of an existing one?","Choose new for new construction, renovation for work in an existing building.","project.new_or_renovation","choice",True,F1,["new","renovation"]),
q("c8","C","What is the main code requirement you want to do differently?","For the demo topic this is the requirement to provide at least two exits from a floor area. Say it plainly; the tool will find the article.","variance.code_or_standard","text",True,PAB4),
q("c9","C","Describe your proposed alternative in plain words.","What you will do instead of the second exit (for example one exit stair with added protection). Do not claim it is safe or equal; just say what you propose.","variance.proposed_alternative.summary","text",True,PAB8),
q("c10","C","Which protective measures will you add (mitigations)?","List what you plan, for example stair enclosure and fire separation, smoke control, sprinklers, fire department access. Pick from the catalogue in the next screen or add your own.","variance.proposed_alternative.mitigations","text",True,{"doc":"11_Edmonton_Point_Access_Block.pdf","page":5}),
q("c11","C","Do you already have reports, drawings, standards or listings that support the proposal?","List names and dates (for example a fire protection engineer's report). These are attached in Section D.","section_d","text",False,F2),
q("d1","D","Which registered professional (architect or engineer) is involved?","Edmonton requires registered architect and/or engineers for a Point Access Block. Give name and firm, or say none yet.","section_d.professional.name","text",True,PAB8),
q("d2","D","Is a qualified Fire Protection or Life Safety Code Consultant preparing the Alternative Solution?","Edmonton requires the Alternative Solution for a Point Access Block to be prepared by one. If no, the tool stops and tells you what is needed.","section_d.consultant_engaged","bool",True,PAB8),
q("d3","D","Have you booked or held a pre-application meeting with the City?","Recommended by Edmonton for Point Access Block proposals. Optional but helpful.","section_d.pre_application_meeting","bool",False,PAB7),
]
json.dump(Q,open("intake_questions.json","w",encoding="utf-8"),indent=1,ensure_ascii=False)
print(len(Q))
