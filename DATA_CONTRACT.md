



# 8. CSV File Formats

All dataset CSV files must follow the exact column names defined below.

## people.csv

```text
person_id
name
dob
gender
city
```

Example header:

```csv
person_id,name,dob,gender,city
```

---

## cdr.csv

```text
cdr_id
caller_phone
receiver_phone
timestamp
duration_seconds
tower_location
case_id
```

Example header:

```csv
cdr_id,caller_phone,receiver_phone,timestamp,duration_seconds,tower_location,case_id
```

---

## transactions.csv

```text
transaction_id
sender_account
receiver_account
amount
timestamp
case_id
```

Example header:

```csv
transaction_id,sender_account,receiver_account,amount,timestamp,case_id
```

---

## vehicles.csv

```text
vehicle_id
registration_number
person_id
```

Example header:

```csv
vehicle_id,registration_number,person_id
```

---

## fir.csv

```text
fir_id
case_id
date
police_station
complaint_text
```

Example header:

```csv
fir_id,case_id,date,police_station,complaint_text
```

---

## surveillance.csv

```text
surveillance_id
case_id
timestamp
location
report_text
```

Example header:

```csv
surveillance_id,case_id,timestamp,location,report_text
```

---

# 9. Dataset Safety Rule

All data used for development and testing must be synthetic or fictional.

Do not use real people's sensitive information such as:

* Real phone numbers
* Real bank account numbers
* Real FIR records
* Real criminal records
* Real financial transactions
* Private surveillance information


