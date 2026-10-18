import logging
import time

logger = logging.getLogger("sellflow.notifications")

def send_order_notification(order_id: int, status: str, customer_email: str):
    '''
    Simulates sending an email/SMS notification.
    In production, replace this with actual SendGrid/Twilio/FCM API calls.
    '''
    logger.info(f"[BACKGROUND] Starting notification for Order #{order_id} to {customer_email}")
    
    # Simulate network delay of an external API call
    time.sleep(1)
    
    logger.info(f"[BACKGROUND] Successfully 'sent' {status} notification for Order #{order_id}")
    return True
