from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
import db_helper
import generic_helper
app = FastAPI()
inprogress_order=dict()

@app.post("/")
async def handle_request(request: dict):
    intent = request["queryResult"]["intent"]["displayName"]
    parameters = request["queryResult"]["parameters"]
    output_contexts = request["queryResult"]["outputContexts"]
    session_id=generic_helper.extract_sessionid(output_contexts[0]["name"])
    intent_handler={
        'order.add:context:-on-going-order': add_to_order,
        'order.remove:context:-on-going-order': remove_from_order,
        'order.complete:context:ongoing.order': complete_order,
        'tracking.order:context:-ongoing-tracking': track_order
    }
    print(intent)
    return intent_handler[intent](parameters,session_id)
        
       
    # Handle other intents or return an error response if intent is not recognized
    raise HTTPException(status_code=400, detail="Intent not recognized")

def insert_order_tracking(parameters: dict):
    order_id=int(parameters["number"])
    staus_of_order=db_helper.track_order(order_id)
    if staus_of_order:
        fulfillmentText=f"your order id is {order_id} and the Status in {staus_of_order}"  # Returning a JSON response
    else:
        fulfillmentText=f"No order found for order id {order_id}"
    return {"fulfillmentText":fulfillmentText}

def add_to_order(parameters: dict,session_id: str):
    food_item=parameters["fooditem"]
    food_quantity=parameters["number"]

    if len(food_item)!=len(food_quantity):
        fulfillmentText="Please provide the quantity for both the orders"
    else:
        new_food_dict=dict(zip(food_item, food_quantity))
        if session_id in inprogress_order:
            current_food_dict=inprogress_order[session_id]
            current_food_dict.update(new_food_dict)
            inprogress_order[session_id]=current_food_dict
        else:
            inprogress_order[session_id]=new_food_dict
        order_str=generic_helper.get_str_from_food_dict(inprogress_order[session_id])
        print(inprogress_order)
        fulfillmentText=f"so for you have {order_str} do you need anything else"

    return {"fulfillmentText":fulfillmentText}


def remove_from_order(parameters: dict, session_id: str):
    if session_id not in inprogress_order:
        return {"fulfillmentText": "I'm having a trouble finding your order. Sorry! Can you place a new order please?"}
    
    food_items = parameters["fooditem"]
    current_order = inprogress_order[session_id]

    removed_items = []
    no_such_items = []

    for item in food_items:
        if item not in current_order:
            no_such_items.append(item)
        else:
            removed_items.append(item)
            del current_order[item]

    if len(removed_items) > 0:
        fulfillment_text = f'Removed {",".join(removed_items)} from your order!, Do you need something else'

    if len(no_such_items) > 0:
        fulfillment_text = f' Your current order does not have {",".join(no_such_items)} Do you need something else'

    if len(current_order.keys()) == 0:
        fulfillment_text += " Your order is empty!"
    else:
        order_str = generic_helper.get_str_from_food_dict(current_order)
        fulfillment_text += f" Here is what is left in your order: {order_str} Do you need something else"

    return {"fulfillmentText": fulfillment_text}

def complete_order(parameters: dict, session_id: str):
    if session_id not in inprogress_order:
        fulfillment_text = "I'm having a trouble finding your order. Sorry! Can you place a new order please?"
    else:
        order = inprogress_order[session_id]
        order_id = save_to_db(order)
        if order_id == -1:
            fulfillment_text = "Sorry, I couldn't process your order due to a backend error. " \
                               "Please place a new order again"
        else:
            order_total = db_helper.get_total_order_price(order_id)

            fulfillment_text = f"Awesome. We have placed your order. " \
                           f"Here is your order id # {order_id}. " \
                           f"Your order total is {order_total} which you can pay at the time of delivery!"

        del inprogress_order[session_id]

    return {
        "fulfillmentText": fulfillment_text}


def track_order(parameters: dict, session_id: str):
    order_id = int(parameters['number'])
    order_status = db_helper.get_order_status(order_id)
    if order_status:
        fulfillment_text = f"The order status for order id: {order_id} is: {order_status}"
    else:
        fulfillment_text = f"No order found with order id: {order_id}"

    return {
        "fulfillmentText": fulfillment_text
    }

def save_to_db(order: dict):
    next_order_id = db_helper.get_next_order_id()

    # Insert individual items along with quantity in orders table
    for food_item, quantity in order.items():
        rcode = db_helper.insert_order_item(
            food_item,
            quantity,
            next_order_id
        )
        if rcode == -1:
            return -1

    # Now insert order tracking status
    db_helper.insert_order_tracking(next_order_id, "in progress")

    return next_order_id