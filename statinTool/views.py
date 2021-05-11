from datetime import date

import fhirclient.models.patient as p
import fhirclient.models.procedure as pro
import requests
from django.http import HttpResponse
from django.template import loader
from django.views.decorators.csrf import csrf_exempt
import fhirclient.models.observation as obs
from fhirclient import client
from fhirclient.models import bundle
import pandas
import os
import re


# Create your views here.
settings = {
    'app_id': 'my_web_app',
    'api_base': 'https://r4.smarthealthit.org'
}
smart = client.FHIRClient(settings=settings)

# since proof of concept, we use a dictionary, but this is where we connect to patient database
patient_db = {
    "Mr. Barrett Cummings": "494743a2-fea5-4827-8f02-c2b91e4a4c9e",
    "Mrs. Raeann O'Kon": "881f534f-d041-425d-a542-cbf669f43e18",
    "Mrs. Twanda Rippin": "b85d7e00-3690-4e2a-87a0-f3d2dfc908b3",
    "Mr. Mario Dietrich":"1fc53917-6bc1-4f87-9008-c91e94f0e188",
    "Mr. David Alcántar": "dc877b20-081d-4109-9e97-99f0fdc58287",
    "Mr. Marcos Barrows": "c4d8bbb7-7214-4260-8a67-065f51f0af18",
    "Mrs. Natalia Ruelas": "d809375c-fef0-42fa-8529-603016123ea5",
    "Mrs. Reba Nolan": "9da7d8c2-daef-4722-832e-dcf495d13a4e",
}

# reading the medical "database" for hypertension and high blood pressure medications
df = pandas.read_csv('statinTool/meds.csv')
meds_list = df.index.tolist()


# calculator code found at: https://github.com/videntity/python-framingham10yr
def framingham_10year_risk(sex, age, total_cholesterol, hdl_cholesterol,
                           systolic_blood_pressure, smoker,
                           blood_pressure_med_treatment):
    """Requires:
        sex                             - "male" or "female" string
        age                             - string or int
        total_cholesterol               - sting or int 
        hdl_cholesterol                 - int
        systolic_blood_pressure         - int
        smoker                          - True or False. Also accepts 1 or 0 as
                                          a string or an int
        blood_pressure_med_treatment    - True or False. Also accepts 1 or 0
                                          as a string or an int
    """
    
    #be liberal in what we accept...massage the input
    if sex in ("MALE", "m", "M", "boy", "xy", "male", "Male"):
        sex = "male"
    if sex in ("FEMALE", "f", "F", "girl", "xx", "female", "Female"):
        sex = "female"    
    
    if smoker in ("yes", "Y", "y", "YES", "true", "t", "True", True, 1, "1"):
        smoker=True
    if smoker in ("no", "NO", "N", "n", "false", "f", "False", False, 0, "0"):
        smoker=False
    if  blood_pressure_med_treatment in ("yes", "Y", "y", "YES", "true", "t",
                                         "True", True, 1, "1"):
        blood_pressure_med_treatment = True
    if  blood_pressure_med_treatment  in ("no", "NO", "N", "n", "false", "f",
                                          "False", False, 0, "0"):
        blood_pressure_med_treatment = False

    #intialize some things -----------------------------------------------------
    errors = [] #a list of errors
    points = 0 
    age = int(age)
    total_cholesterol = int(total_cholesterol)
    hdl_cholesterol = int(hdl_cholesterol)
    systolic_blood_pressure = int(systolic_blood_pressure)
    
    try:
        blood_pressure_med_treatment = bool(int(blood_pressure_med_treatment))
    except(ValueError):
        errors.append("Blood pressure medication treatment must be set to True, False, 1, 0, yes, or no.")
    
    try:
        smoker = bool(int(smoker))
    except(ValueError):
        errors.append("Smoker must be set to True, False, 1, 0, yes, or no.")
        
    
    # Intitalize our response dictionary
    response = {"status": 200,
                "sex":sex,
                "message": "OK",
                "age": age,
                "total_cholesterol": total_cholesterol,  
                "hdl_cholesterol" : hdl_cholesterol,
                "systolic_blood_pressure": systolic_blood_pressure,
                "smoker": smoker,
                "blood_pressure_med_treatment": blood_pressure_med_treatment,
                }
    
    
    #run some sanity checks ----------------------------------------------------
    if not 20 <= age <=79:
        errors.append("Age must be within the range of 20 to 79.")
    
    if not 130 <= total_cholesterol <= 320:
        errors.append("Total cholesterol must be within the range of 130 to 320.")
    
    if not 20 <= hdl_cholesterol <= 100:
        errors.append("HDL cholesterol must be within the range of 20 to 100.")
    
    if not 90 <= systolic_blood_pressure<= 200:
        errors.append("Systolic blood pressure must be within the range of 90 to 200.")
    
    if sex.lower() not in ('male', 'female'):
        errors.append("Sex must be male or female.")

    #Process males -----------------------------------------------------------
    if sex.lower()=="male":

        # Age - male        
        if  20 <= age <= 34:
            points-=9
        if  35 <= age <= 39:
            points-=4
        if  40 <= age <= 44:
            points-=0
        if  45 <= age <= 49:
            points+=3
        if  50 <= age <= 54:
            points+=6
        if  55 <= age <= 59:
            points+=8
        if  60 <= age <= 64:
            points+=10
        if  65 <= age <= 69:
            points+=12
        if  70 <= age <= 74:
            points+=14
        if  75 <= age <= 79:
            points+=16

        #Total cholesterol, mg/dL - Male ------------------------
        if  20 <= age <= 39:
            if total_cholesterol < 160:
                points +=0
            if 160 <= total_cholesterol <= 199:
                points+=4
            if 200 <= total_cholesterol <= 239:
                points+=7
            if 240 <= total_cholesterol <= 279:
                points+=9
            if total_cholesterol > 289:
                points+=11
        if  40 <= age <= 49:
            if total_cholesterol < 160:
                points +=0
            if 160 <= total_cholesterol <= 199:
                points+=3
            if 200 <= total_cholesterol <= 239:
                points+=5
            if 240 <= total_cholesterol <= 279:
                points+=6
            if total_cholesterol > 289:
                points+=8
        if  50 <= age <= 59:
            if total_cholesterol < 160:
                points +=0
            if 160 <= total_cholesterol <= 199:
                points+=2
            if 200 <= total_cholesterol <= 239:
                points+=3
            if 240 <= total_cholesterol <= 279:
                points+=4
            if total_cholesterol > 289:
                points+=5
        if  60 <= age <= 69:
            if total_cholesterol < 160:
                points +=0
            if 160 <= total_cholesterol <= 199:
                points+=1
            if 200 <= total_cholesterol <= 239:
                points+=1
            if 240 <= total_cholesterol <= 279:
                points+=2
            if total_cholesterol > 289:
                points+=3
        if  70 <= age <= 79:
            if total_cholesterol < 160:
                points +=0
            if 160 <= total_cholesterol <= 199:
                points+=0
            if 200 <= total_cholesterol <= 239:
                points+=0
            if 240 <= total_cholesterol <= 279:
                points+=1
            if total_cholesterol > 289:
                points+=1
        #smoking - male
        if smoker:
            if 20 <= age <= 39:
               points+=8 
            if 40 <= age <= 49:
               points+=5
            if 50 <= age <= 59:
               points+=3
            if 60 <= age <= 69:
               points+=1
            if 70 <= age <= 79:
               points+=1 
        else: # nonsmoker
            points += 0
         
        #hdl cholesterol
        if hdl_cholesterol > 60:
            points-=1
        if 50 <= hdl_cholesterol <= 59:
            points+=0
        if 40 <= hdl_cholesterol <= 49:
            points+=1
        if hdl_cholesterol < 40:
            points+=2
            
        #systolic blood pressure
        if not blood_pressure_med_treatment:
            if systolic_blood_pressure < 120:
                points+=0
            if 120 <= systolic_blood_pressure <= 129:
                points+=0
            if 130 <= systolic_blood_pressure <= 139:
                points+=1           
            if 140 <= systolic_blood_pressure <= 159:
                points+=1
            if systolic_blood_pressure >= 160:
                points +=2
        else: #if the patient is on blood pressure meds
            if systolic_blood_pressure < 120:
                points+=0
            if 120 <= systolic_blood_pressure <= 129:
                points+=1
            if 130 <= systolic_blood_pressure <= 139:
                points+=1           
            if 140 <= systolic_blood_pressure <= 159:
                points+=2
            if systolic_blood_pressure >= 160:
                points +=3
        
        #calulate % risk for males
        if points <= 0:
            percent_risk ="<1%"
        elif points == 1:
            percent_risk ="1%"
        
        elif points == 2:
            percent_risk ="1%"
            
        elif points == 3:
            percent_risk ="1%"
            
        elif points == 4:
            percent_risk ="1%"
            
        elif points == 5:
            percent_risk ="2%"
            
        elif points == 6:
            percent_risk ="2%"
            
        elif points == 7:
            percent_risk ="2%"
            
        elif points == 8:
            percent_risk ="2%"
            
        elif points == 9:
            percent_risk ="5%"
            
        elif points == 10:
            percent_risk ="6%"
            
        elif points == 11:
            percent_risk ="8%"
            
        elif points == 12:
            percent_risk ="10%"
            
        elif points == 13:
            percent_risk ="12%"

        elif points == 14:
            percent_risk ="16%"
            
        elif points == 15:
            percent_risk ="20%"
            
        elif points == 16:
            percent_risk ="25%"
            
        elif points >= 17:
            percent_risk =">30%"
            
    #process females ----------------------------------------------------------
    elif sex.lower()=="female":
        # Age - female        
        if  20 <= age <= 34:
            points-=7
        if  35 <= age <= 39:
            points-=3
        if  40 <= age <= 44:
            points-=0
        if  45 <= age <= 49:
            points+=3
        if  50 <= age <= 54:
            points+=6
        if  55 <= age <= 59:
            points+=8
        if  60 <= age <= 64:
            points+=10
        if  65 <= age <= 69:
            points+=12
        if  70 <= age <= 74:
            points+=14
        if  75 <= age <= 79:
            points+=16

        #Total cholesterol, mg/dL - Female ------------------------
        if  20 <= age <= 39:
            if total_cholesterol < 160:
                points +=0
            if 160 <= total_cholesterol <= 199:
                points+=4
            if 200 <= total_cholesterol <= 239:
                points+=8
            if 240 <= total_cholesterol <= 279:
                points+=11
            if total_cholesterol > 289:
                points+=13
        if  40 <= age <= 49:
            if total_cholesterol < 160:
                points +=0
            if 160 <= total_cholesterol <= 199:
                points+=3
            if 200 <= total_cholesterol <= 239:
                points+=6
            if 240 <= total_cholesterol <= 279:
                points+=8
            if total_cholesterol > 289:
                points+=10
        if  50 <= age <= 59:
            if total_cholesterol < 160:
                points +=0
            if 160 <= total_cholesterol <= 199:
                points+=2
            if 200 <= total_cholesterol <= 239:
                points+=4
            if 240 <= total_cholesterol <= 279:
                points+=5
            if total_cholesterol > 289:
                points+=7
        if  60 <= age <= 69:
            if total_cholesterol < 160:
                points +=0
            if 160 <= total_cholesterol <= 199:
                points+=1
            if 200 <= total_cholesterol <= 239:
                points+=2
            if 240 <= total_cholesterol <= 279:
                points+=3
            if total_cholesterol > 289:
                points+=4
        if  70 <= age <= 79:
            if total_cholesterol < 160:
                points +=0
            if 160 <= total_cholesterol <= 199:
                points+=1
            if 200 <= total_cholesterol <= 239:
                points+=1
            if 240 <= total_cholesterol <= 279:
                points+=2
            if total_cholesterol > 289:
                points+=2
        #smoking - female
        if smoker:
            if 20 <= age <= 39:
               points+=9 
            if 40 <= age <= 49:
               points+=7
            if 50 <= age <= 59:
               points+=4
            if 60 <= age <= 69:
               points+=2
            if 70 <= age <= 79:
               points+=1 
        else: #nonsmoker
            points += 0
         
        #hdl cholesterol - female
        if hdl_cholesterol > 60:
            points-=1
        if 50 <= hdl_cholesterol <= 59:
            points+=0
        if 40 <= hdl_cholesterol <= 49:
            points+=1
        if hdl_cholesterol < 40:
            points+=2
            
        #systolic blood pressure
        if not blood_pressure_med_treatment: #untreated
            if systolic_blood_pressure < 120:
                points+=0
            if 120 <= systolic_blood_pressure <= 129:
                points+=1
            if 130 <= systolic_blood_pressure <= 139:
                points+=2           
            if 140 <= systolic_blood_pressure <= 159:
                points+=3
            if systolic_blood_pressure >= 160:
                points +=4
        else: #if the patient is on blood pressure meds
            if systolic_blood_pressure < 120:
                points+=0
            if 120 <= systolic_blood_pressure <= 129:
                points+=3
            if 130 <= systolic_blood_pressure <= 139:
                points+=4           
            if 140 <= systolic_blood_pressure <= 159:
                points+=5
            if systolic_blood_pressure >= 160:
                points +=6
        
        #calulate % risk for females
        if points <= 9:
            percent_risk ="<1%"
        elif 9 <= points <= 12:
            percent_risk ="1%"
        
        elif 13 <= points <= 14:
            percent_risk ="2%"
            
        elif points == 15:
            percent_risk ="3%"
            

        elif points == 16:
            percent_risk ="4%"
            
        elif points == 17:
            percent_risk ="5%"
            
        elif points == 18:
            percent_risk ="6%"

        elif points == 19:
            percent_risk ="8%"
            
        elif points == 20:
            percent_risk ="11%"
            
        elif points == 21:
            percent_risk ="14%"
            
        elif points == 22:
            percent_risk ="17%"

        elif points == 23:
            percent_risk ="22%"
            
        elif points == 24:
            percent_risk ="27%"
            
        elif points >= 25:
            percent_risk ="30%"

    if errors:
        response['status']=422
        response['message'] = "The request contained errors and was unable to process."
        response['errors']=errors
    else:
        response['points']=points
        
        
        
        
        
        
        
        
        response['percent_risk']= percent_risk
    
    return response

@csrf_exempt
def home(request):
    template = loader.get_template('statin_tool.html')
    context = {}
    print(request.POST.get('patients', False))
    if request.POST.get('patients', False) != 'empty':
        context = {'name': request.POST.get('patients', False), "pats": patient_db}
    if request.method == 'POST' and request.POST.get('patients', False) != 'empty':
        print(request.POST['patients'])
        p_id = patient_db[request.POST.get('patients', False)]
        sex = ''
        age = 0
        total_cholesterol = 0
        hdl_cholesterol = 0
        systolic_blood_pressure = 0
        smoker = 0
        blood_pressure_med_treatment = 0


        headers = {"Content-Type": "application/fhir+json"}
        patient = p.Patient.read(p_id, smart.server)
        sex = patient.gender
        age = date.today().year - int(patient.birthDate.as_json()[:4])

        tc_api = requests.get('https://r4.smarthealthit.org/Observation?category=laboratory&patient=' + p_id + '&_sort=-date&code=http://loinc.org|2093-3', headers=headers)
        total_cholesterol = tc_api.json()['entry'][0]['resource']['valueQuantity']['value']
        
        hdl_api = requests.get('https://r4.smarthealthit.org/Observation?category=laboratory&patient=' + p_id + '&_sort=-date&code=http://loinc.org|2085-9', headers=headers)
        hdl_cholesterol = hdl_api.json()['entry'][0]['resource']['valueQuantity']['value']
        
        sbp_api = requests.get('https://r4.smarthealthit.org/Observation?category=vital-signs&patient=' + p_id + '&code=http://loinc.org|55284-4&_sort=-date', headers=headers)
        systolic_blood_pressure = sbp_api.json()['entry'][0]['resource']['component'][1]['valueQuantity']['value']
        
        s_api = requests.get('https://r4.smarthealthit.org/Observation?&patient=' + p_id + '&code=http://loinc.org|72166-2&_sort=-date&_count=50', headers=headers)
        result = s_api.json()['entry'][0]['resource']['valueCodeableConcept']['text']
        if result == 'Never smoker' or result == 'Former smoker' or result == 'Unknown if ever smoked':
            smoker = 0
        else:
            smoker = 1

        meds_api = requests.get('https://r4.smarthealthit.org/MedicationRequest?&patient=' + p_id + '&_sort=-date', headers=headers)
        med_treatment = False
        for req in meds_api.json()['entry']:
            med = req['resource']['medicationCodeableConcept']['text'].split()[0]
            if 'statin' in med or med in meds_list:
                med_treatment = req['resource']['status'] == 'active'
                if med_treatment:
                    break

        # calling the calculator
        calculation = framingham_10year_risk(sex=sex, age=age, total_cholesterol=total_cholesterol, hdl_cholesterol=hdl_cholesterol, systolic_blood_pressure=systolic_blood_pressure,
                            smoker=smoker, blood_pressure_med_treatment=med_treatment)
        
        # checking if the calculation was a success
        if calculation['status'] == 200:
            result = calculation
            risk = re.findall('\d+\.*\d*', result['percent_risk'])
            if float(risk[0]) > 20:
                recommendation = 'The patient has a high 10-year ASCVD risk. A high-intensity statin is recommended. Please prescribe either 40 mg - 80 mg of Atorvastatin or 20 mg - 40 mg of Rosuvastation. Please discuss these options with the patient.'
            elif float(risk[0]) > 7.5:
                recommendation = '''The patient has a moderate 10-year ASCVD risk. A moderate-intensity statin is recommended. Please prescribe either 10 mg - 20 mg of Atorvastatin,
                                    5 mg - 10 mg of Rosuvastation, 40 mg of Lovastatin, 20 mg - 40 mg of Simvastatin, 40 mg - 80 mg of Pravastatin, 80 mg of Fluvastatin (XL), 40 mg (twice daily) of Fluvastatin, or 2 mg - 4 mg of Pitavastatin. Please discuss these options with the patient.'''
            else:
                recommendation = 'The patient has a low 10-year ASCVD risk. A low-intensity statin is recommended. Please prescribe either 20 mg of Lovastatin, 10 mg of Simvastatin, 10 mg - 20 mg of Pravastatin, 20 - 40 mg of Fluvastatin, or 1 mg of Pitavastatin. Please discuss these options with the patient.'
            context = {
                "result": result,
                "percent": result['percent_risk'],
                "recommendation": recommendation, 
                "name": request.POST.get('patients', False),
                "pats": patient_db
            }
        else:
            result = calculation['errors']
            context = {
                "result": result,

            }

    return HttpResponse(template.render(context, request))

    # patient = p.Patient.read('494743a2-fea5-4827-8f02-c2b91e4a4c9e', smart.server)
    # search = obs.Observation.where(struct={'subject': 'Patient/494743a2-fea5-4827-8f02-c2b91e4a4c9e'})
    #
    # observations = search.perform_resources(smart.server)
    # d_t = ''
    # d_h = ''
    # d_c = ''
    # d_s = ''
    # for observation in observations:
    #     if observation.as_json()['code']['coding'][0]['display'] == 'Total Cholesterol':
    #         if d_t < observation.as_json()['issued']:
    #             total_cholesterol = observation.as_json()['valueQuantity']['value']
    #             d_t = observation.as_json()['issued']
    #
    #     if observation.as_json()['code']['coding'][0]['display'] == 'High Density Lipoprotein Cholesterol':
    #         if d_h < observation.as_json()['issued']:
    #             hdl_cholesterol = observation.as_json()['valueQuantity']['value']
    #             d_h = observation.as_json()['issued']
    #
    #     if 'component' in observation.as_json().keys():
    #         for component in observation.as_json()['component']:
    #             if component['code']['text'] == 'Systolic Blood Pressure' and d_c < observation.as_json()['issued']:
    #                 systolic_blood_pressure = component['valueQuantity']['value']
    #                 d_c = observation.as_json()['issued']
    # # for observation in observations
    #     if 'valueCodeableConcept' in observation.as_json():
    #         if observation.as_json()['valueCodeableConcept']['text'] == 'Never Smoker' or observation.as_json()['valueCodeableConcept']['text'] == 'Former Smoker':
    #             smoker = 0
    #         if observation.as_json()['valueCodeableConcept']['text'] == 'Current Smoker':
    #             smoker = 1

