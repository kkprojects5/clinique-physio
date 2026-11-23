# ZAP Scanning Report

ZAP by [Checkmarx](https://checkmarx.com/).


## Summary of Alerts

| Risk Level | Number of Alerts |
| --- | --- |
| High | 0 |
| Medium | 0 |
| Low | 0 |
| Informational | 7 |




## Insights

| Level | Reason | Site | Description | Statistic |
| --- | --- | --- | --- | --- |
| Medium | Exceeded High | http://localhost:8000 | Percentage of responses with status code 4xx | 99 % |
| Low | Warning |  | ZAP warnings logged - see the zap.log file for details | 15    |
| Info | Informational | http://localhost:8000 | Percentage of responses with status code 2xx | 1 % |
| Info | Informational | http://localhost:8000 | Percentage of endpoints with content type application/json | 100 % |
| Info | Informational | http://localhost:8000 | Percentage of endpoints with method DELETE | 2 % |
| Info | Informational | http://localhost:8000 | Percentage of endpoints with method GET | 63 % |
| Info | Informational | http://localhost:8000 | Percentage of endpoints with method PATCH | 5 % |
| Info | Informational | http://localhost:8000 | Percentage of endpoints with method POST | 25 % |
| Info | Informational | http://localhost:8000 | Percentage of endpoints with method PUT | 2 % |
| Info | Informational | http://localhost:8000 | Count of total endpoints | 256    |







## Alerts

| Name | Risk Level | Number of Instances |
| --- | --- | --- |
| A Client Error response code was returned by the server | Informational | 262 |
| Authentication Request Identified | Informational | 1 |
| Non-Storable Content | Informational | Systemic |
| Sec-Fetch-Dest Header is Missing | Informational | 3 |
| Sec-Fetch-Mode Header is Missing | Informational | 3 |
| Sec-Fetch-Site Header is Missing | Informational | 3 |
| Sec-Fetch-User Header is Missing | Informational | 3 |




## Alert Detail



### [ A Client Error response code was returned by the server ](https://www.zaproxy.org/docs/alerts/100000/)



##### Informational (High)

### Description

A response code of 422 was returned by the server.
This may indicate that the application is failing to handle unexpected input correctly.
Raised by the 'Alert on HTTP Response Code Error' script

* URL: http://localhost:8000/api/v1/admin/therapists/therapist_id/photo
  * Node Name: `http://localhost:8000/api/v1/admin/therapists/therapist_id/photo`
  * Method: `DELETE`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/admin/therapists/therapist_id/photo/
  * Node Name: `http://localhost:8000/api/v1/admin/therapists/therapist_id/photo/`
  * Method: `DELETE`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/me/program/check-offs/log_id
  * Node Name: `http://localhost:8000/api/v1/me/program/check-offs/log_id`
  * Method: `DELETE`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/me/program/check-offs/log_id/
  * Node Name: `http://localhost:8000/api/v1/me/program/check-offs/log_id/`
  * Method: `DELETE`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/therapist/availability/exceptions/exception_id
  * Node Name: `http://localhost:8000/api/v1/therapist/availability/exceptions/exception_id`
  * Method: `DELETE`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/therapist/availability/exceptions/exception_id/
  * Node Name: `http://localhost:8000/api/v1/therapist/availability/exceptions/exception_id/`
  * Method: `DELETE`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000
  * Node Name: `http://localhost:8000`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/
  * Node Name: `http://localhost:8000/`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/5941286023620267201
  * Node Name: `http://localhost:8000/5941286023620267201`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api
  * Node Name: `http://localhost:8000/api`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/
  * Node Name: `http://localhost:8000/api/`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/4960674426487321179
  * Node Name: `http://localhost:8000/api/4960674426487321179`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1
  * Node Name: `http://localhost:8000/api/v1`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/
  * Node Name: `http://localhost:8000/api/v1/`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/278380936322364366
  * Node Name: `http://localhost:8000/api/v1/278380936322364366`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/admin
  * Node Name: `http://localhost:8000/api/v1/admin`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/admin/
  * Node Name: `http://localhost:8000/api/v1/admin/`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/admin/8608426467200582225
  * Node Name: `http://localhost:8000/api/v1/admin/8608426467200582225`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/admin/audit
  * Node Name: `http://localhost:8000/api/v1/admin/audit`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/admin/audit%3Fdate_from=&date_to=&action=&resource_type=&actor_email=&patient_id=&before_id=&limit=50
  * Node Name: `http://localhost:8000/api/v1/admin/audit (action,actor_email,before_id,date_from,date_to,limit,patient_id,resource_type)`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/admin/audit/
  * Node Name: `http://localhost:8000/api/v1/admin/audit/`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/admin/incidents
  * Node Name: `http://localhost:8000/api/v1/admin/incidents`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/admin/incidents/
  * Node Name: `http://localhost:8000/api/v1/admin/incidents/`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/admin/incidents/5131123950551708530
  * Node Name: `http://localhost:8000/api/v1/admin/incidents/5131123950551708530`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `405`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/admin/incidents/actuator/health
  * Node Name: `http://localhost:8000/api/v1/admin/incidents/actuator/health`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/admin/privacy-requests
  * Node Name: `http://localhost:8000/api/v1/admin/privacy-requests`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/admin/privacy-requests/
  * Node Name: `http://localhost:8000/api/v1/admin/privacy-requests/`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/admin/privacy-requests/8025789789422982491
  * Node Name: `http://localhost:8000/api/v1/admin/privacy-requests/8025789789422982491`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `405`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/admin/privacy-requests/request_id
  * Node Name: `http://localhost:8000/api/v1/admin/privacy-requests/request_id`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `405`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/admin/privacy-requests/request_id/
  * Node Name: `http://localhost:8000/api/v1/admin/privacy-requests/request_id/`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `405`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/admin/privacy-requests/request_id/3890251352047666271
  * Node Name: `http://localhost:8000/api/v1/admin/privacy-requests/request_id/3890251352047666271`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/admin/privacy-requests/request_id/export
  * Node Name: `http://localhost:8000/api/v1/admin/privacy-requests/request_id/export`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/admin/privacy-requests/request_id/export/
  * Node Name: `http://localhost:8000/api/v1/admin/privacy-requests/request_id/export/`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/admin/reports
  * Node Name: `http://localhost:8000/api/v1/admin/reports`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/admin/reports/
  * Node Name: `http://localhost:8000/api/v1/admin/reports/`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/admin/reports/6350503255181418756
  * Node Name: `http://localhost:8000/api/v1/admin/reports/6350503255181418756`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/admin/reports/weekly
  * Node Name: `http://localhost:8000/api/v1/admin/reports/weekly`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/admin/reports/weekly%3Fweek=
  * Node Name: `http://localhost:8000/api/v1/admin/reports/weekly (week)`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/admin/reports/weekly/
  * Node Name: `http://localhost:8000/api/v1/admin/reports/weekly/`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/admin/services
  * Node Name: `http://localhost:8000/api/v1/admin/services`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/admin/services/
  * Node Name: `http://localhost:8000/api/v1/admin/services/`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/admin/services/6205184060911811410
  * Node Name: `http://localhost:8000/api/v1/admin/services/6205184060911811410`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `405`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/admin/staff
  * Node Name: `http://localhost:8000/api/v1/admin/staff`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/admin/staff/
  * Node Name: `http://localhost:8000/api/v1/admin/staff/`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/admin/staff/4246800323655709071
  * Node Name: `http://localhost:8000/api/v1/admin/staff/4246800323655709071`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `405`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/admin/staff/user_id
  * Node Name: `http://localhost:8000/api/v1/admin/staff/user_id`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `405`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/admin/staff/user_id/
  * Node Name: `http://localhost:8000/api/v1/admin/staff/user_id/`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `405`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/admin/staff/user_id/2912850334354278005
  * Node Name: `http://localhost:8000/api/v1/admin/staff/user_id/2912850334354278005`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/admin/therapists
  * Node Name: `http://localhost:8000/api/v1/admin/therapists`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/admin/therapists/
  * Node Name: `http://localhost:8000/api/v1/admin/therapists/`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/admin/therapists/7899808277226738073
  * Node Name: `http://localhost:8000/api/v1/admin/therapists/7899808277226738073`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/admin/therapists/therapist_id
  * Node Name: `http://localhost:8000/api/v1/admin/therapists/therapist_id`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/admin/therapists/therapist_id/
  * Node Name: `http://localhost:8000/api/v1/admin/therapists/therapist_id/`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/admin/therapists/therapist_id/4245297217210600158
  * Node Name: `http://localhost:8000/api/v1/admin/therapists/therapist_id/4245297217210600158`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/appointments
  * Node Name: `http://localhost:8000/api/v1/appointments`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/appointments/
  * Node Name: `http://localhost:8000/api/v1/appointments/`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/appointments/5496829972055239183
  * Node Name: `http://localhost:8000/api/v1/appointments/5496829972055239183`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/appointments/appointment_id
  * Node Name: `http://localhost:8000/api/v1/appointments/appointment_id`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/appointments/appointment_id/
  * Node Name: `http://localhost:8000/api/v1/appointments/appointment_id/`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/appointments/appointment_id/1257920515452912265
  * Node Name: `http://localhost:8000/api/v1/appointments/appointment_id/1257920515452912265`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/appointments/appointment_id/receipt
  * Node Name: `http://localhost:8000/api/v1/appointments/appointment_id/receipt`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/appointments/appointment_id/receipt/
  * Node Name: `http://localhost:8000/api/v1/appointments/appointment_id/receipt/`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/auth
  * Node Name: `http://localhost:8000/api/v1/auth`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/auth/
  * Node Name: `http://localhost:8000/api/v1/auth/`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/auth/8193376116593968333
  * Node Name: `http://localhost:8000/api/v1/auth/8193376116593968333`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/auth/mfa
  * Node Name: `http://localhost:8000/api/v1/auth/mfa`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/auth/mfa/
  * Node Name: `http://localhost:8000/api/v1/auth/mfa/`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/auth/mfa/8961642060367178867
  * Node Name: `http://localhost:8000/api/v1/auth/mfa/8961642060367178867`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/auth/password
  * Node Name: `http://localhost:8000/api/v1/auth/password`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/auth/password/
  * Node Name: `http://localhost:8000/api/v1/auth/password/`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/auth/password/3757186845071897066
  * Node Name: `http://localhost:8000/api/v1/auth/password/3757186845071897066`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/availability
  * Node Name: `http://localhost:8000/api/v1/availability`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `422`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/availability%3Fservice_id=service_id&date_from=date_from&date_to=date_to&therapist_id=
  * Node Name: `http://localhost:8000/api/v1/availability (date_from,date_to,service_id,therapist_id)`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `422`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/availability/
  * Node Name: `http://localhost:8000/api/v1/availability/`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `422`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/chat
  * Node Name: `http://localhost:8000/api/v1/chat`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/chat/
  * Node Name: `http://localhost:8000/api/v1/chat/`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/chat/3543126892017217558
  * Node Name: `http://localhost:8000/api/v1/chat/3543126892017217558`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/desk
  * Node Name: `http://localhost:8000/api/v1/desk`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/desk/
  * Node Name: `http://localhost:8000/api/v1/desk/`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/desk/6431658514210074440
  * Node Name: `http://localhost:8000/api/v1/desk/6431658514210074440`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/desk/appointments
  * Node Name: `http://localhost:8000/api/v1/desk/appointments`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `405`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/desk/appointments/
  * Node Name: `http://localhost:8000/api/v1/desk/appointments/`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `405`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/desk/appointments/1808024786767357498
  * Node Name: `http://localhost:8000/api/v1/desk/appointments/1808024786767357498`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/desk/appointments/appointment_id
  * Node Name: `http://localhost:8000/api/v1/desk/appointments/appointment_id`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/desk/appointments/appointment_id/
  * Node Name: `http://localhost:8000/api/v1/desk/appointments/appointment_id/`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/desk/appointments/appointment_id/2876829156342003145
  * Node Name: `http://localhost:8000/api/v1/desk/appointments/appointment_id/2876829156342003145`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/desk/appointments/appointment_id/billing
  * Node Name: `http://localhost:8000/api/v1/desk/appointments/appointment_id/billing`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/desk/appointments/appointment_id/billing/
  * Node Name: `http://localhost:8000/api/v1/desk/appointments/appointment_id/billing/`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/desk/appointments/appointment_id/receipt
  * Node Name: `http://localhost:8000/api/v1/desk/appointments/appointment_id/receipt`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/desk/appointments/appointment_id/receipt%3Flang=fr
  * Node Name: `http://localhost:8000/api/v1/desk/appointments/appointment_id/receipt (lang)`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/desk/appointments/appointment_id/receipt/
  * Node Name: `http://localhost:8000/api/v1/desk/appointments/appointment_id/receipt/`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/desk/patients
  * Node Name: `http://localhost:8000/api/v1/desk/patients`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/desk/patients%3Fq=q
  * Node Name: `http://localhost:8000/api/v1/desk/patients (q)`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/desk/patients/
  * Node Name: `http://localhost:8000/api/v1/desk/patients/`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/desk/schedule
  * Node Name: `http://localhost:8000/api/v1/desk/schedule`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/desk/schedule%3Fdate=date
  * Node Name: `http://localhost:8000/api/v1/desk/schedule (date)`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/desk/schedule/
  * Node Name: `http://localhost:8000/api/v1/desk/schedule/`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/me
  * Node Name: `http://localhost:8000/api/v1/me`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/me/
  * Node Name: `http://localhost:8000/api/v1/me/`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/me/6920618568304785968
  * Node Name: `http://localhost:8000/api/v1/me/6920618568304785968`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/me/appointments
  * Node Name: `http://localhost:8000/api/v1/me/appointments`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/me/appointments/
  * Node Name: `http://localhost:8000/api/v1/me/appointments/`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/me/privacy-requests
  * Node Name: `http://localhost:8000/api/v1/me/privacy-requests`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/me/privacy-requests/
  * Node Name: `http://localhost:8000/api/v1/me/privacy-requests/`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/me/program
  * Node Name: `http://localhost:8000/api/v1/me/program`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/me/program/
  * Node Name: `http://localhost:8000/api/v1/me/program/`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/me/program/3937900538860033453
  * Node Name: `http://localhost:8000/api/v1/me/program/3937900538860033453`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/me/program/check-offs
  * Node Name: `http://localhost:8000/api/v1/me/program/check-offs`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/me/program/check-offs/
  * Node Name: `http://localhost:8000/api/v1/me/program/check-offs/`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/me/program/check-offs/752805378329820292
  * Node Name: `http://localhost:8000/api/v1/me/program/check-offs/752805378329820292`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `405`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/me/program/items
  * Node Name: `http://localhost:8000/api/v1/me/program/items`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/me/program/items/
  * Node Name: `http://localhost:8000/api/v1/me/program/items/`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/me/program/items/3875349478395851708
  * Node Name: `http://localhost:8000/api/v1/me/program/items/3875349478395851708`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/me/program/items/item_id
  * Node Name: `http://localhost:8000/api/v1/me/program/items/item_id`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/me/program/items/item_id/
  * Node Name: `http://localhost:8000/api/v1/me/program/items/item_id/`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/me/program/items/item_id/8619765827689485421
  * Node Name: `http://localhost:8000/api/v1/me/program/items/item_id/8619765827689485421`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/me/receipts
  * Node Name: `http://localhost:8000/api/v1/me/receipts`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/me/receipts/
  * Node Name: `http://localhost:8000/api/v1/me/receipts/`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/staff
  * Node Name: `http://localhost:8000/api/v1/staff`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/staff/
  * Node Name: `http://localhost:8000/api/v1/staff/`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/staff/3783936461571792631
  * Node Name: `http://localhost:8000/api/v1/staff/3783936461571792631`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/staff/session
  * Node Name: `http://localhost:8000/api/v1/staff/session`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/staff/session/
  * Node Name: `http://localhost:8000/api/v1/staff/session/`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/therapist
  * Node Name: `http://localhost:8000/api/v1/therapist`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/therapist/
  * Node Name: `http://localhost:8000/api/v1/therapist/`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/therapist/8538504147634568624
  * Node Name: `http://localhost:8000/api/v1/therapist/8538504147634568624`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/therapist/appointments
  * Node Name: `http://localhost:8000/api/v1/therapist/appointments`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/therapist/appointments/
  * Node Name: `http://localhost:8000/api/v1/therapist/appointments/`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/therapist/appointments/3579303669277608339
  * Node Name: `http://localhost:8000/api/v1/therapist/appointments/3579303669277608339`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/therapist/appointments/appointment_id
  * Node Name: `http://localhost:8000/api/v1/therapist/appointments/appointment_id`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/therapist/appointments/appointment_id/
  * Node Name: `http://localhost:8000/api/v1/therapist/appointments/appointment_id/`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/therapist/appointments/appointment_id/2181124316623003012
  * Node Name: `http://localhost:8000/api/v1/therapist/appointments/appointment_id/2181124316623003012`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/therapist/availability
  * Node Name: `http://localhost:8000/api/v1/therapist/availability`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/therapist/availability/
  * Node Name: `http://localhost:8000/api/v1/therapist/availability/`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/therapist/availability/8959428742993515863
  * Node Name: `http://localhost:8000/api/v1/therapist/availability/8959428742993515863`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/therapist/availability/exceptions
  * Node Name: `http://localhost:8000/api/v1/therapist/availability/exceptions`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `405`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/therapist/availability/exceptions/
  * Node Name: `http://localhost:8000/api/v1/therapist/availability/exceptions/`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `405`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/therapist/availability/exceptions/346123538373775851
  * Node Name: `http://localhost:8000/api/v1/therapist/availability/exceptions/346123538373775851`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `405`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/therapist/me
  * Node Name: `http://localhost:8000/api/v1/therapist/me`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/therapist/me/
  * Node Name: `http://localhost:8000/api/v1/therapist/me/`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/therapist/notes
  * Node Name: `http://localhost:8000/api/v1/therapist/notes`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/therapist/notes/
  * Node Name: `http://localhost:8000/api/v1/therapist/notes/`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/therapist/notes/987509713431206341
  * Node Name: `http://localhost:8000/api/v1/therapist/notes/987509713431206341`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/therapist/notes/note_id
  * Node Name: `http://localhost:8000/api/v1/therapist/notes/note_id`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/therapist/notes/note_id/
  * Node Name: `http://localhost:8000/api/v1/therapist/notes/note_id/`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/therapist/notes/note_id/8166424588300518411
  * Node Name: `http://localhost:8000/api/v1/therapist/notes/note_id/8166424588300518411`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/therapist/patients
  * Node Name: `http://localhost:8000/api/v1/therapist/patients`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/therapist/patients/
  * Node Name: `http://localhost:8000/api/v1/therapist/patients/`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/therapist/patients/2943914759545921128
  * Node Name: `http://localhost:8000/api/v1/therapist/patients/2943914759545921128`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/therapist/patients/patient_id
  * Node Name: `http://localhost:8000/api/v1/therapist/patients/patient_id`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/therapist/patients/patient_id/
  * Node Name: `http://localhost:8000/api/v1/therapist/patients/patient_id/`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/therapist/patients/patient_id/8535233834607694905
  * Node Name: `http://localhost:8000/api/v1/therapist/patients/patient_id/8535233834607694905`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/therapist/patients/patient_id/notes
  * Node Name: `http://localhost:8000/api/v1/therapist/patients/patient_id/notes`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/therapist/patients/patient_id/notes/
  * Node Name: `http://localhost:8000/api/v1/therapist/patients/patient_id/notes/`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/therapist/patients/patient_id/programs
  * Node Name: `http://localhost:8000/api/v1/therapist/patients/patient_id/programs`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/therapist/patients/patient_id/programs/
  * Node Name: `http://localhost:8000/api/v1/therapist/patients/patient_id/programs/`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/therapists/6307589515735099548
  * Node Name: `http://localhost:8000/api/v1/therapists/6307589515735099548`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/therapists/therapist_id
  * Node Name: `http://localhost:8000/api/v1/therapists/therapist_id`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/therapists/therapist_id/
  * Node Name: `http://localhost:8000/api/v1/therapists/therapist_id/`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/therapists/therapist_id/4267904087765467502
  * Node Name: `http://localhost:8000/api/v1/therapists/therapist_id/4267904087765467502`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/therapists/therapist_id/photo
  * Node Name: `http://localhost:8000/api/v1/therapists/therapist_id/photo`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `422`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/therapists/therapist_id/photo/
  * Node Name: `http://localhost:8000/api/v1/therapists/therapist_id/photo/`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `422`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/webhooks
  * Node Name: `http://localhost:8000/api/v1/webhooks`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/webhooks/
  * Node Name: `http://localhost:8000/api/v1/webhooks/`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/webhooks/2654876903538538079
  * Node Name: `http://localhost:8000/api/v1/webhooks/2654876903538538079`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/admin/incidents/incident_id
  * Node Name: `http://localhost:8000/api/v1/admin/incidents/incident_id ()({"description":Zaproxy alias impedit expedita quisquam pariatur exercitationem. Nemo rerum eveniet dolores rem quia dignissimos.,"data_categories":"John Doe","people_affected":10,"risk_level":"low","measures":"John Doe","cai_notified_at":"1970-01-01T00:00:00.001Z","persons_notified_at":"1970-01-01T00:00:00.001Z"})`
  * Method: `PATCH`
  * Parameter: ``
  * Attack: ``
  * Evidence: `422`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/admin/incidents/incident_id/
  * Node Name: `http://localhost:8000/api/v1/admin/incidents/incident_id/ ()({"description":Zaproxy alias impedit expedita quisquam pariatur exercitationem. Nemo rerum eveniet dolores rem quia dignissimos.,"data_categories":"John Doe","people_affected":10,"risk_level":"low","measures":"John Doe","cai_notified_at":"1970-01-01T00:00:00.001Z","persons_notified_at":"1970-01-01T00:00:00.001Z"})`
  * Method: `PATCH`
  * Parameter: ``
  * Attack: ``
  * Evidence: `422`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/admin/privacy-requests/request_id
  * Node Name: `http://localhost:8000/api/v1/admin/privacy-requests/request_id ()({status,outcome})`
  * Method: `PATCH`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/admin/privacy-requests/request_id/
  * Node Name: `http://localhost:8000/api/v1/admin/privacy-requests/request_id/ ()({status,outcome})`
  * Method: `PATCH`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/admin/services/service_id
  * Node Name: `http://localhost:8000/api/v1/admin/services/service_id ()({name_fr,name_en,description_fr,description_en,duration_min,price_cents,deposit_cents,is_initial_evaluation,is_active,therapist_ids:[]})`
  * Method: `PATCH`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/admin/services/service_id/
  * Node Name: `http://localhost:8000/api/v1/admin/services/service_id/ ()({name_fr,name_en,description_fr,description_en,duration_min,price_cents,deposit_cents,is_initial_evaluation,is_active,therapist_ids:[]})`
  * Method: `PATCH`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/admin/staff/user_id
  * Node Name: `http://localhost:8000/api/v1/admin/staff/user_id ()({is_active})`
  * Method: `PATCH`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/admin/staff/user_id/
  * Node Name: `http://localhost:8000/api/v1/admin/staff/user_id/ ()({is_active})`
  * Method: `PATCH`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/computeMetadata/v1/
  * Node Name: `http://localhost:8000/computeMetadata/v1/ ()({"description":Zaproxy alias impedit expedita quisquam pariatur exercitationem. Nemo rerum eveniet dolores rem quia dignissimos.,"data_categories":"John Doe","people_affected":10,"risk_level":"low","measures":"John Doe","cai_notified_at":"1970-01-01T00:00:00.001Z","persons_notified_at":"1970-01-01T00:00:00.001Z"})`
  * Method: `PATCH`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/latest/meta-data/
  * Node Name: `http://localhost:8000/latest/meta-data/ ()({"description":Zaproxy alias impedit expedita quisquam pariatur exercitationem. Nemo rerum eveniet dolores rem quia dignissimos.,"data_categories":"John Doe","people_affected":10,"risk_level":"low","measures":"John Doe","cai_notified_at":"1970-01-01T00:00:00.001Z","persons_notified_at":"1970-01-01T00:00:00.001Z"})`
  * Method: `PATCH`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/metadata/instance
  * Node Name: `http://localhost:8000/metadata/instance ()({"description":Zaproxy alias impedit expedita quisquam pariatur exercitationem. Nemo rerum eveniet dolores rem quia dignissimos.,"data_categories":"John Doe","people_affected":10,"risk_level":"low","measures":"John Doe","cai_notified_at":"1970-01-01T00:00:00.001Z","persons_notified_at":"1970-01-01T00:00:00.001Z"})`
  * Method: `PATCH`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/metadata/v1
  * Node Name: `http://localhost:8000/metadata/v1 ()({"description":Zaproxy alias impedit expedita quisquam pariatur exercitationem. Nemo rerum eveniet dolores rem quia dignissimos.,"data_categories":"John Doe","people_affected":10,"risk_level":"low","measures":"John Doe","cai_notified_at":"1970-01-01T00:00:00.001Z","persons_notified_at":"1970-01-01T00:00:00.001Z"})`
  * Method: `PATCH`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/opc/v1/instance/
  * Node Name: `http://localhost:8000/opc/v1/instance/ ()({"description":Zaproxy alias impedit expedita quisquam pariatur exercitationem. Nemo rerum eveniet dolores rem quia dignissimos.,"data_categories":"John Doe","people_affected":10,"risk_level":"low","measures":"John Doe","cai_notified_at":"1970-01-01T00:00:00.001Z","persons_notified_at":"1970-01-01T00:00:00.001Z"})`
  * Method: `PATCH`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/opc/v2/instance/
  * Node Name: `http://localhost:8000/opc/v2/instance/ ()({"description":Zaproxy alias impedit expedita quisquam pariatur exercitationem. Nemo rerum eveniet dolores rem quia dignissimos.,"data_categories":"John Doe","people_affected":10,"risk_level":"low","measures":"John Doe","cai_notified_at":"1970-01-01T00:00:00.001Z","persons_notified_at":"1970-01-01T00:00:00.001Z"})`
  * Method: `PATCH`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/openstack/latest/meta_data.json
  * Node Name: `http://localhost:8000/openstack/latest/meta_data.json ()({"description":Zaproxy alias impedit expedita quisquam pariatur exercitationem. Nemo rerum eveniet dolores rem quia dignissimos.,"data_categories":"John Doe","people_affected":10,"risk_level":"low","measures":"John Doe","cai_notified_at":"1970-01-01T00:00:00.001Z","persons_notified_at":"1970-01-01T00:00:00.001Z"})`
  * Method: `PATCH`
  * Parameter: ``
  * Attack: ``
  * Evidence: `404`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/admin/incidents
  * Node Name: `http://localhost:8000/api/v1/admin/incidents ()({occurred_at,discovered_at,description,data_categories,people_affected,risk_level,measures,cai_notified_at,persons_notified_at})`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/admin/incidents/
  * Node Name: `http://localhost:8000/api/v1/admin/incidents/ ()({occurred_at,discovered_at,description,data_categories,people_affected,risk_level,measures,cai_notified_at,persons_notified_at})`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/admin/privacy-requests/request_id/erase
  * Node Name: `http://localhost:8000/api/v1/admin/privacy-requests/request_id/erase`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/admin/privacy-requests/request_id/erase/
  * Node Name: `http://localhost:8000/api/v1/admin/privacy-requests/request_id/erase/`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/admin/services
  * Node Name: `http://localhost:8000/api/v1/admin/services ()({name_fr,name_en,description_fr,description_en,duration_min,price_cents,deposit_cents,is_initial_evaluation,therapist_ids:[]})`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/admin/services/
  * Node Name: `http://localhost:8000/api/v1/admin/services/ ()({name_fr,name_en,description_fr,description_en,duration_min,price_cents,deposit_cents,is_initial_evaluation,therapist_ids:[]})`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/admin/staff
  * Node Name: `http://localhost:8000/api/v1/admin/staff ()({email,role,language,therapist:{first_name,last_name,licence_number,languages:[]}})`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/admin/staff/
  * Node Name: `http://localhost:8000/api/v1/admin/staff/ ()({email,role,language,therapist:{first_name,last_name,licence_number,languages:[]}})`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/admin/staff/user_id/invitation
  * Node Name: `http://localhost:8000/api/v1/admin/staff/user_id/invitation`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/admin/staff/user_id/invitation/
  * Node Name: `http://localhost:8000/api/v1/admin/staff/user_id/invitation/`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/appointments/appointment_id/cancel
  * Node Name: `http://localhost:8000/api/v1/appointments/appointment_id/cancel`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/appointments/appointment_id/cancel/
  * Node Name: `http://localhost:8000/api/v1/appointments/appointment_id/cancel/`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/appointments/appointment_id/pay
  * Node Name: `http://localhost:8000/api/v1/appointments/appointment_id/pay`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/appointments/appointment_id/pay/
  * Node Name: `http://localhost:8000/api/v1/appointments/appointment_id/pay/`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/appointments/appointment_id/reschedule
  * Node Name: `http://localhost:8000/api/v1/appointments/appointment_id/reschedule ()({start,therapist_id})`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/appointments/appointment_id/reschedule/
  * Node Name: `http://localhost:8000/api/v1/appointments/appointment_id/reschedule/ ()({start,therapist_id})`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/appointments/hold
  * Node Name: `http://localhost:8000/api/v1/appointments/hold ()({service_id,therapist_id,start})`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/appointments/hold/
  * Node Name: `http://localhost:8000/api/v1/appointments/hold/ ()({service_id,therapist_id,start})`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/auth/login
  * Node Name: `http://localhost:8000/api/v1/auth/login ()({email,password})`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/auth/login
  * Node Name: `http://localhost:8000/api/v1/auth/login ()({email,password})`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `422`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/auth/login
  * Node Name: `http://localhost:8000/api/v1/auth/login ()({email,password})`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `429`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/auth/login/
  * Node Name: `http://localhost:8000/api/v1/auth/login/ ()({email,password})`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `429`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/auth/mfa/setup
  * Node Name: `http://localhost:8000/api/v1/auth/mfa/setup ()({mfa_token})`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/auth/mfa/setup
  * Node Name: `http://localhost:8000/api/v1/auth/mfa/setup ()({mfa_token})`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `422`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/auth/mfa/setup
  * Node Name: `http://localhost:8000/api/v1/auth/mfa/setup ()({mfa_token})`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `429`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/auth/mfa/setup/
  * Node Name: `http://localhost:8000/api/v1/auth/mfa/setup/ ()({mfa_token})`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `429`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/auth/mfa/verify
  * Node Name: `http://localhost:8000/api/v1/auth/mfa/verify ()({mfa_token,code})`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `422`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/auth/mfa/verify/
  * Node Name: `http://localhost:8000/api/v1/auth/mfa/verify/ ()({mfa_token,code})`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `422`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/auth/password/forgot
  * Node Name: `http://localhost:8000/api/v1/auth/password/forgot ()({email})`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `422`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/auth/password/forgot
  * Node Name: `http://localhost:8000/api/v1/auth/password/forgot ()({email})`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `429`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/auth/password/reset
  * Node Name: `http://localhost:8000/api/v1/auth/password/reset ()({token,new_password})`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `400`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/auth/password/reset
  * Node Name: `http://localhost:8000/api/v1/auth/password/reset ()({token,new_password})`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `422`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/auth/password/reset
  * Node Name: `http://localhost:8000/api/v1/auth/password/reset ()({token,new_password})`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `429`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/auth/password/reset/
  * Node Name: `http://localhost:8000/api/v1/auth/password/reset/ ()({token,new_password})`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `422`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/auth/refresh
  * Node Name: `http://localhost:8000/api/v1/auth/refresh`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/auth/refresh/
  * Node Name: `http://localhost:8000/api/v1/auth/refresh/`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/auth/register
  * Node Name: `http://localhost:8000/api/v1/auth/register ()({email,password,first_name,last_name,date_of_birth,phone,language,emergency_contact,accept_privacy_policy,accept_electronic_comms})`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `422`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/auth/register
  * Node Name: `http://localhost:8000/api/v1/auth/register ()({email,password,first_name,last_name,date_of_birth,phone,language,emergency_contact,accept_privacy_policy,accept_electronic_comms})`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `429`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/auth/register/
  * Node Name: `http://localhost:8000/api/v1/auth/register/ ()({email,password,first_name,last_name,date_of_birth,phone,language,emergency_contact,accept_privacy_policy,accept_electronic_comms})`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `422`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/auth/verify-email
  * Node Name: `http://localhost:8000/api/v1/auth/verify-email ()({token})`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `400`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/auth/verify-email
  * Node Name: `http://localhost:8000/api/v1/auth/verify-email ()({token})`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `422`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/auth/verify-email
  * Node Name: `http://localhost:8000/api/v1/auth/verify-email ()({token})`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `429`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/auth/verify-email/
  * Node Name: `http://localhost:8000/api/v1/auth/verify-email/ ()({token})`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `429`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/chat/feedback
  * Node Name: `http://localhost:8000/api/v1/chat/feedback ()({message_id,helpful})`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `422`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/chat/feedback/
  * Node Name: `http://localhost:8000/api/v1/chat/feedback/ ()({message_id,helpful})`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `422`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/chat/messages
  * Node Name: `http://localhost:8000/api/v1/chat/messages ()({message,language})`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `422`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/chat/messages
  * Node Name: `http://localhost:8000/api/v1/chat/messages ()({message,language})`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `429`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/chat/messages/
  * Node Name: `http://localhost:8000/api/v1/chat/messages/ ()({message,language})`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `429`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/desk/appointments
  * Node Name: `http://localhost:8000/api/v1/desk/appointments ()({patient_id,service_id,therapist_id,start})`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/desk/appointments/
  * Node Name: `http://localhost:8000/api/v1/desk/appointments/ ()({patient_id,service_id,therapist_id,start})`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/desk/appointments/appointment_id/cancel
  * Node Name: `http://localhost:8000/api/v1/desk/appointments/appointment_id/cancel`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/desk/appointments/appointment_id/cancel/
  * Node Name: `http://localhost:8000/api/v1/desk/appointments/appointment_id/cancel/`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/desk/appointments/appointment_id/check-in
  * Node Name: `http://localhost:8000/api/v1/desk/appointments/appointment_id/check-in`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/desk/appointments/appointment_id/check-in/
  * Node Name: `http://localhost:8000/api/v1/desk/appointments/appointment_id/check-in/`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/desk/appointments/appointment_id/no-show
  * Node Name: `http://localhost:8000/api/v1/desk/appointments/appointment_id/no-show`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/desk/appointments/appointment_id/no-show/
  * Node Name: `http://localhost:8000/api/v1/desk/appointments/appointment_id/no-show/`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/desk/appointments/appointment_id/payments
  * Node Name: `http://localhost:8000/api/v1/desk/appointments/appointment_id/payments ()({method})`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/desk/appointments/appointment_id/payments/
  * Node Name: `http://localhost:8000/api/v1/desk/appointments/appointment_id/payments/ ()({method})`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/desk/appointments/appointment_id/reschedule
  * Node Name: `http://localhost:8000/api/v1/desk/appointments/appointment_id/reschedule ()({start,therapist_id})`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/desk/appointments/appointment_id/reschedule/
  * Node Name: `http://localhost:8000/api/v1/desk/appointments/appointment_id/reschedule/ ()({start,therapist_id})`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/me/privacy-requests
  * Node Name: `http://localhost:8000/api/v1/me/privacy-requests ()({type,details})`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/me/privacy-requests/
  * Node Name: `http://localhost:8000/api/v1/me/privacy-requests/ ()({type,details})`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/me/program/items/item_id/check-off
  * Node Name: `http://localhost:8000/api/v1/me/program/items/item_id/check-off ()({pain_level})`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/me/program/items/item_id/check-off/
  * Node Name: `http://localhost:8000/api/v1/me/program/items/item_id/check-off/ ()({pain_level})`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/therapist/appointments/appointment_id/notes
  * Node Name: `http://localhost:8000/api/v1/therapist/appointments/appointment_id/notes ()({subjective,objective,assessment,plan})`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/therapist/appointments/appointment_id/notes/
  * Node Name: `http://localhost:8000/api/v1/therapist/appointments/appointment_id/notes/ ()({subjective,objective,assessment,plan})`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/therapist/availability/exceptions
  * Node Name: `http://localhost:8000/api/v1/therapist/availability/exceptions ()({starts_at,ends_at,reason})`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/therapist/availability/exceptions/
  * Node Name: `http://localhost:8000/api/v1/therapist/availability/exceptions/ ()({starts_at,ends_at,reason})`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/therapist/notes/note_id/amendments
  * Node Name: `http://localhost:8000/api/v1/therapist/notes/note_id/amendments ()({subjective,objective,assessment,plan})`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/therapist/notes/note_id/amendments/
  * Node Name: `http://localhost:8000/api/v1/therapist/notes/note_id/amendments/ ()({subjective,objective,assessment,plan})`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/therapist/notes/note_id/sign
  * Node Name: `http://localhost:8000/api/v1/therapist/notes/note_id/sign`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/therapist/notes/note_id/sign/
  * Node Name: `http://localhost:8000/api/v1/therapist/notes/note_id/sign/`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/therapist/patients/patient_id/programs
  * Node Name: `http://localhost:8000/api/v1/therapist/patients/patient_id/programs ()({start_date,weeks,notes,items:[{exercise_id,sets,reps,times_per_week}]})`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/therapist/patients/patient_id/programs/
  * Node Name: `http://localhost:8000/api/v1/therapist/patients/patient_id/programs/ ()({start_date,weeks,notes,items:[{exercise_id,sets,reps,times_per_week}]})`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/webhooks/stripe
  * Node Name: `http://localhost:8000/api/v1/webhooks/stripe`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `400`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/webhooks/stripe/
  * Node Name: `http://localhost:8000/api/v1/webhooks/stripe/`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `400`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/admin/therapists/therapist_id/photo
  * Node Name: `http://localhost:8000/api/v1/admin/therapists/therapist_id/photo`
  * Method: `PUT`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/admin/therapists/therapist_id/photo/
  * Node Name: `http://localhost:8000/api/v1/admin/therapists/therapist_id/photo/`
  * Method: `PUT`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/therapist/availability
  * Node Name: `http://localhost:8000/api/v1/therapist/availability ()({rules:[{weekday,start_time,end_time}]})`
  * Method: `PUT`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/therapist/availability/
  * Node Name: `http://localhost:8000/api/v1/therapist/availability/ ()({rules:[{weekday,start_time,end_time}]})`
  * Method: `PUT`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/therapist/notes/note_id
  * Node Name: `http://localhost:8000/api/v1/therapist/notes/note_id ()({subjective,objective,assessment,plan})`
  * Method: `PUT`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/therapist/notes/note_id/
  * Node Name: `http://localhost:8000/api/v1/therapist/notes/note_id/ ()({subjective,objective,assessment,plan})`
  * Method: `PUT`
  * Parameter: ``
  * Attack: ``
  * Evidence: `401`
  * Other Info: ``


Instances: 262

### Solution



### Reference



#### CWE Id: [ 388 ](https://cwe.mitre.org/data/definitions/388.html)


#### WASC Id: 20

#### Source ID: 4

### [ Authentication Request Identified ](https://www.zaproxy.org/docs/alerts/10111/)



##### Informational (High)

### Description

The given request has been identified as an authentication request. The 'Other Info' field contains a set of key=value lines which identify any relevant fields. If the request is in a context which has an Authentication Method set to "Auto-Detect" then this rule will change the authentication to match the request identified.

* URL: http://localhost:8000/api/v1/auth/login
  * Node Name: `http://localhost:8000/api/v1/auth/login ()({email,password})`
  * Method: `POST`
  * Parameter: `email`
  * Attack: ``
  * Evidence: `password`
  * Other Info: `userParam=email
userValue=zaproxy@example.com
passwordParam=password`


Instances: 1

### Solution

This is an informational alert rather than a vulnerability and so there is nothing to fix.

### Reference


* [ https://www.zaproxy.org/docs/desktop/addons/authentication-helper/auth-req-id/ ](https://www.zaproxy.org/docs/desktop/addons/authentication-helper/auth-req-id/)



#### Source ID: 3

### [ Non-Storable Content ](https://www.zaproxy.org/docs/alerts/10049/)



##### Informational (Medium)

### Description

The response contents are not storable by caching components such as proxy servers. If the response does not contain sensitive, personal or user-specific information, it may benefit from being stored and cached, to improve performance.

* URL: http://localhost:8000/openapi.json
  * Node Name: `http://localhost:8000/openapi.json`
  * Method: `GET`
  * Parameter: ``
  * Attack: ``
  * Evidence: `no-store`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/auth/login
  * Node Name: `http://localhost:8000/api/v1/auth/login ()({email,password})`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `no-store`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/auth/mfa/setup
  * Node Name: `http://localhost:8000/api/v1/auth/mfa/setup ()({mfa_token})`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `no-store`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/auth/register
  * Node Name: `http://localhost:8000/api/v1/auth/register ()({email,password,first_name,last_name,date_of_birth,phone,language,emergency_contact,accept_privacy_policy,accept_electronic_comms})`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `no-store`
  * Other Info: ``
* URL: http://localhost:8000/api/v1/auth/verify-email
  * Node Name: `http://localhost:8000/api/v1/auth/verify-email ()({token})`
  * Method: `POST`
  * Parameter: ``
  * Attack: ``
  * Evidence: `no-store`
  * Other Info: ``

Instances: Systemic


### Solution

The content may be marked as storable by ensuring that the following conditions are satisfied:
The request method must be understood by the cache and defined as being cacheable ("GET", "HEAD", and "POST" are currently defined as cacheable)
The response status code must be understood by the cache (one of the 1XX, 2XX, 3XX, 4XX, or 5XX response classes are generally understood)
The "no-store" cache directive must not appear in the request or response header fields
For caching by "shared" caches such as "proxy" caches, the "private" response directive must not appear in the response
For caching by "shared" caches such as "proxy" caches, the "Authorization" header field must not appear in the request, unless the response explicitly allows it (using one of the "must-revalidate", "public", or "s-maxage" Cache-Control response directives)
In addition to the conditions above, at least one of the following conditions must also be satisfied by the response:
It must contain an "Expires" header field
It must contain a "max-age" response directive
For "shared" caches such as "proxy" caches, it must contain a "s-maxage" response directive
It must contain a "Cache Control Extension" that allows it to be cached
It must have a status code that is defined as cacheable by default (200, 203, 204, 206, 300, 301, 404, 405, 410, 414, 501).

### Reference


* [ https://datatracker.ietf.org/doc/html/rfc7234 ](https://datatracker.ietf.org/doc/html/rfc7234)
* [ https://datatracker.ietf.org/doc/html/rfc7231 ](https://datatracker.ietf.org/doc/html/rfc7231)
* [ https://www.w3.org/Protocols/rfc2616/rfc2616-sec13.html ](https://www.w3.org/Protocols/rfc2616/rfc2616-sec13.html)


#### CWE Id: [ 524 ](https://cwe.mitre.org/data/definitions/524.html)


#### WASC Id: 13

#### Source ID: 3

### [ Sec-Fetch-Dest Header is Missing ](https://www.zaproxy.org/docs/alerts/90005/)



##### Informational (High)

### Description

Specifies how and where the data would be used. For instance, if the value is audio, then the requested resource must be audio data and not any other type of resource.

* URL: http://localhost:8000/openapi.json
  * Node Name: `http://localhost:8000/openapi.json`
  * Method: `GET`
  * Parameter: `Sec-Fetch-Dest`
  * Attack: ``
  * Evidence: ``
  * Other Info: ``
* URL: http://localhost:8000/api/v1/auth/register
  * Node Name: `http://localhost:8000/api/v1/auth/register ()({email,password,first_name,last_name,date_of_birth,phone,language,emergency_contact,accept_privacy_policy,accept_electronic_comms})`
  * Method: `POST`
  * Parameter: `Sec-Fetch-Dest`
  * Attack: ``
  * Evidence: ``
  * Other Info: ``
* URL: http://localhost:8000/api/v1/auth/verify-email
  * Node Name: `http://localhost:8000/api/v1/auth/verify-email ()({token})`
  * Method: `POST`
  * Parameter: `Sec-Fetch-Dest`
  * Attack: ``
  * Evidence: ``
  * Other Info: ``


Instances: 3

### Solution

Ensure that Sec-Fetch-Dest header is included in request headers.

### Reference


* [ https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Sec-Fetch-Dest ](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Sec-Fetch-Dest)


#### CWE Id: [ 352 ](https://cwe.mitre.org/data/definitions/352.html)


#### WASC Id: 9

#### Source ID: 3

### [ Sec-Fetch-Mode Header is Missing ](https://www.zaproxy.org/docs/alerts/90005/)



##### Informational (High)

### Description

Allows to differentiate between requests for navigating between HTML pages and requests for loading resources like images, audio etc.

* URL: http://localhost:8000/openapi.json
  * Node Name: `http://localhost:8000/openapi.json`
  * Method: `GET`
  * Parameter: `Sec-Fetch-Mode`
  * Attack: ``
  * Evidence: ``
  * Other Info: ``
* URL: http://localhost:8000/api/v1/auth/register
  * Node Name: `http://localhost:8000/api/v1/auth/register ()({email,password,first_name,last_name,date_of_birth,phone,language,emergency_contact,accept_privacy_policy,accept_electronic_comms})`
  * Method: `POST`
  * Parameter: `Sec-Fetch-Mode`
  * Attack: ``
  * Evidence: ``
  * Other Info: ``
* URL: http://localhost:8000/api/v1/auth/verify-email
  * Node Name: `http://localhost:8000/api/v1/auth/verify-email ()({token})`
  * Method: `POST`
  * Parameter: `Sec-Fetch-Mode`
  * Attack: ``
  * Evidence: ``
  * Other Info: ``


Instances: 3

### Solution

Ensure that Sec-Fetch-Mode header is included in request headers.

### Reference


* [ https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Sec-Fetch-Mode ](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Sec-Fetch-Mode)


#### CWE Id: [ 352 ](https://cwe.mitre.org/data/definitions/352.html)


#### WASC Id: 9

#### Source ID: 3

### [ Sec-Fetch-Site Header is Missing ](https://www.zaproxy.org/docs/alerts/90005/)



##### Informational (High)

### Description

Specifies the relationship between request initiator's origin and target's origin.

* URL: http://localhost:8000/openapi.json
  * Node Name: `http://localhost:8000/openapi.json`
  * Method: `GET`
  * Parameter: `Sec-Fetch-Site`
  * Attack: ``
  * Evidence: ``
  * Other Info: ``
* URL: http://localhost:8000/api/v1/auth/register
  * Node Name: `http://localhost:8000/api/v1/auth/register ()({email,password,first_name,last_name,date_of_birth,phone,language,emergency_contact,accept_privacy_policy,accept_electronic_comms})`
  * Method: `POST`
  * Parameter: `Sec-Fetch-Site`
  * Attack: ``
  * Evidence: ``
  * Other Info: ``
* URL: http://localhost:8000/api/v1/auth/verify-email
  * Node Name: `http://localhost:8000/api/v1/auth/verify-email ()({token})`
  * Method: `POST`
  * Parameter: `Sec-Fetch-Site`
  * Attack: ``
  * Evidence: ``
  * Other Info: ``


Instances: 3

### Solution

Ensure that Sec-Fetch-Site header is included in request headers.

### Reference


* [ https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Sec-Fetch-Site ](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Sec-Fetch-Site)


#### CWE Id: [ 352 ](https://cwe.mitre.org/data/definitions/352.html)


#### WASC Id: 9

#### Source ID: 3

### [ Sec-Fetch-User Header is Missing ](https://www.zaproxy.org/docs/alerts/90005/)



##### Informational (High)

### Description

Specifies if a navigation request was initiated by a user.

* URL: http://localhost:8000/openapi.json
  * Node Name: `http://localhost:8000/openapi.json`
  * Method: `GET`
  * Parameter: `Sec-Fetch-User`
  * Attack: ``
  * Evidence: ``
  * Other Info: ``
* URL: http://localhost:8000/api/v1/auth/register
  * Node Name: `http://localhost:8000/api/v1/auth/register ()({email,password,first_name,last_name,date_of_birth,phone,language,emergency_contact,accept_privacy_policy,accept_electronic_comms})`
  * Method: `POST`
  * Parameter: `Sec-Fetch-User`
  * Attack: ``
  * Evidence: ``
  * Other Info: ``
* URL: http://localhost:8000/api/v1/auth/verify-email
  * Node Name: `http://localhost:8000/api/v1/auth/verify-email ()({token})`
  * Method: `POST`
  * Parameter: `Sec-Fetch-User`
  * Attack: ``
  * Evidence: ``
  * Other Info: ``


Instances: 3

### Solution

Ensure that Sec-Fetch-User header is included in user initiated requests.

### Reference


* [ https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Sec-Fetch-User ](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Sec-Fetch-User)


#### CWE Id: [ 352 ](https://cwe.mitre.org/data/definitions/352.html)


#### WASC Id: 9

#### Source ID: 3


