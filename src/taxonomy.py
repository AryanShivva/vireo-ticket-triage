"""Issue taxonomy + ordered regex rules. Rules are applied to text that has been lower-cased.
Each issue maps to (true_category, owning_team). Order matters: first match wins."""
import re

ISSUES = {
 # issue_key: (category, owning_team)
 'delivery_not_received': ('Delivery & Shipping','Logistics'),
 'wrong_item':            ('Delivery & Shipping','Logistics'),
 'transit_damage':        ('Delivery & Shipping','Logistics'),
 'address_change':        ('Delivery & Shipping','Logistics'),
 'refund_status':         ('Returns & Refunds','Returns Desk'),
 'return_pickup':         ('Returns & Refunds','Returns Desk'),
 'dup_or_failed_payment': ('Billing & Payments','Billing'),
 'invoice_gst':           ('Billing & Payments','Billing'),
 'price_coupon':          ('Billing & Payments','Billing'),
 'cancellation':          ('Billing & Payments','Billing'),
 'warranty_rma':          ('Warranty & Repair','Escalations & Warranty'),
 'hw_defect':             ('Warranty & Repair','Escalations & Warranty'),   # strap/touch/display/dead unit
 'connectivity':          ('Connectivity','Frontline'),
 'battery_charging':      ('Charging & Battery','Frontline'),
 'audio_quality':         ('Audio Quality','Frontline'),
 'app_firmware':          ('App & Firmware','Frontline'),
 'account_login':         ('Account & Login','Frontline'),
 'product_enquiry':       ('Product Enquiry','Frontline'),
}

# (issue, regex). Specific before general.
RULES = [
 ('dup_or_failed_payment', r'(?:charged|billed|paid|debited|deducted|amount|money|payment)\W+(?:\w+\W+){0,4}twice|same (?:amount|money) twice|do[u]?ble (?:pay|charge|debit|deduct)|duplicate (?:pay|charge|txn|transaction)|charged 2|deducted|debited|failed (?:ord|order)|upi shows|page failed|utr|money (?:debit|gone)|amount (?:got )?(?:cut|debit)|no order (?:was )?created|order not showing|nothing shows in my account|where is my stuff'),
 ('invoice_gst',          r'invoice|gst|gstin|tax bill'),
 ('price_coupon',         r'coupon|promo|discount|price (?:drop|adj|match)|% off|cart says|offer (?:not|price)|full price'),
 ('cancellation',         r'cancel|stop the shipment|wrong colou?r, don|change of mind|ord cancellation'),
 ('address_change',       r'address (?:change|update|edit)|change (?:the )?(?:delivery )?address|wrong pincode|pincode|flat number|typo in the (?:flat|address)|house number|edit(?:ing)? (?:the )?address|incorrect address'),
 ('return_pickup',        r'pick-?up|pkp|nobody came|no one showed|rescheduled pickup|reverse pkp'),
 ('refund_status',        r'refu\w*|refn?d|rfn+d|rnfd|rfund|return was accepted|money for the return|amount is nowhere|credited'),
 ('wrong_item',           r'wrong (?:item|product|variant|colou?r)|incorrect product|different thing|got something else|something else|ordered .{0,25} got|completely different|not what i (?:ordered|asked)|got white|got black'),
 ('transit_damage',       r'transit damage|damaged in transit|received damaged|rcvd damaged|arrived (?:broken|damaged|crushed|cracked)|box (?:was )?(?:crushed|damaged)|parcel looked (?:tampered|damaged)|crushed|dent|unit received damaged|damaged product|damaged (?:on|at) arrival'),
 ('account_login',        r'login|log in|logged|otp|password|sign ?in|locked|my account (?:is|got)|account (?:locked|blocked)'),
 ('delivery_not_received',r'not deliver|not rece?i?ve?d|not rcvd|delivery delay|dlvry|delayed|nothing in hand|still (?:not )?here|never arrived|haven.t received|courier|tracking|awb|rto|stuck on shipped|shipment|parcel|marked (?:it )?delivered|where is my (?:order|stuff|package|parcel)|shows? (?:as )?delivered|not arrived|yet to receive|package'),
 ('warranty_rma',         r'rma|warranty|repair|service c(?:e)?ntre|service center|claim number|sent the unit|wty'),
 ('hw_defect',            r'strap|touch|display|unresponsive|screen|dead on arrival|doa|crack(?!l)|water damage|button|dead unit|won.t (?:power|turn)|not turning on|not powering|no power|powering on|power cut|completely dead|no lights'),
 ('battery_charging',     r'batt|charg|case (?:no|dead)|not taking charge|bud no charge|drain|case no led|power bank'),
 ('connectivity',         r'pair|bluetooth|disconnect|dropout|discoverable|connection|connect(?:ivity)?|laptop|wifi|wi-fi|goes silent|stutter'),
 ('audio_quality',        r'audio|sound|distort|crackl|static|mic|noise|bass|volume|one side|silent|muffled|side (?:has no|no)|bud (?:is )?(?:dead|silent)|one of them is just decoration|left side|right side|treble'),
 ('app_firmware',         r'\bapp\b|firmware|\bfw\b|update|crash|ota|software'),
 ('product_enquiry',      r'compat|pre-?sales|enquiry|inquiry|which (?:one|model)|difference between|does it (?:work|support)|will (?:the|it|this) .{0,30}(?:work|run|fit)|available|warranty period|buy|colou?rs? options|spec'),
]

# issue phrase extraction from agent note (first stated problem, not the actions taken)
_ISS = [re.compile(r'issue: ([^.|\n]+)'),
        re.compile(r'(?:re:|reported|states|says|contact(?:ed)? re|reached out(?: re)?|customer reached out -|cx:|contact re|ticket raised for) ?([^.|\n]+)'),
        re.compile(r'^\s*1\. ([^\n|]+)')]
def issue_phrase(note: str):
    """returns (phrase, explicit). explicit=False means we had to guess the first segment of the note."""
    n=(note or '').lower()
    for rx in _ISS:
        m=rx.search(n)
        if m: return m.group(1), True
    return n.split('->')[0].split('|')[0].split('.')[0], False

COMPILED = [(k, re.compile(p)) for k, p in RULES]

def rule_label(text: str):
    t = (text or '').lower().replace('\\n',' ')
    t = re.sub(r'(?:low )?mic (?:pickup|pkp)', 'mic', t)
    for k, rx in COMPILED:
        if rx.search(t):
            return k
    return None

def note_label(note: str):
    ph, explicit = issue_phrase(note)
    return rule_label(ph)

def note_is_explicit(note: str):
    return issue_phrase(note)[1]

_WRONG = re.compile(r'wrong (?:item|product|variant)|got something else|completely different|ordered \w+, got \w+|not what i asked for|incorrect product')
def combined_label(note: str, message: str):
    """Note-first labelling with two guarded message overrides (see README, 'what changed between versions')."""
    nl = note_label(note); ml = rule_label(message)
    if not note_is_explicit(note):                          # vague note ("done", "see prev"): leave to the text model
        return None
    if nl in ('hw_defect','delivery_not_received') and _WRONG.search((message or '').lower()):
        return 'wrong_item'
    return nl
