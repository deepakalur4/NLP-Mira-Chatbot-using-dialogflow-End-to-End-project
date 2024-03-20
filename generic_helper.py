import re
def extract_sessionid(session_str:str):
    matching=re.search(r"/sessions/(.*?)/contexts/",session_str)
    if matching:
        extracted_string=matching.group(1)
        return extracted_string
    return 'not found'

def get_str_from_food_dict(food_dict:dict):
    return ','.join([f"{int(value)} {key}" for key,value in food_dict.items()])

if __name__=="__main__":
    print(get_str_from_food_dict({"samosa":4,"chole":5}))