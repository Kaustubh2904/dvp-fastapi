# Postman Usage Guide

This folder contains a Postman collection for the DVP FastAPI backend and a matching local environment.

## Files

- `DVP-FastAPI.postman_collection.json`: the request collection.
- `DVP-FastAPI.postman_environment.json`: local variables for the collection.

## Import

1. Open Postman.
2. Select **Import**.
3. Import both JSON files from this folder.
4. Choose the `DVP FastAPI Local` environment.

## Configure

Update `base_url` if your API is not running on `http://localhost:8000`.

The collection uses these variables:

- `access_token`
- `refresh_token`
- `company_id`
- `employee_id`
- `department_id`
- `document_id`
- `notification_id`
- `subscription_id`
- `request_id`
- `plan_id`
- `user_id`
- `ticket_id`
- `conversation_id`

## Authenticate

Use one of the requests under **Authentication** first. Successful login requests save `access_token` and `refresh_token` into the active environment.

Recommended flow:

1. Run `Register Company` or `Login`.
2. Run `Me` to auto-fill `user_id`, `company_id`, and `employee_id` from the response.
3. Run protected requests in the other folders.

For manual testing, paste a valid bearer token into `access_token`.

The collection sample data now uses valid values for this codebase, including `DocumentType.AADHAR` and `BillingStatus.ACTIVE`.

## Using File Upload Requests

The following requests expect file inputs in the `form-data` body:

- `Employees > Bulk Upload Employees`
- `Employees > Upload Offer and Joining Letters`
- `Documents > Upload Document`

When Postman opens the request, pick a local file for each `file` field.

## Role Notes

Several endpoints enforce role-based access control. If a request fails with `401`, `403`, or `404`, verify that the current token belongs to a user with the correct role and tenant scope.

Examples:

- `Companies > List Companies` requires `SUPERADMIN`.
- `Employees > Create Employee` requires `ADMIN`.
- `Documents > Upload Document` requires `EMPLOYEE`.
- `Subscriptions` admin actions require subscription admin access.

## Websockets

The API also exposes a websocket endpoint at `/api/v1/ws/chat`. It is not included in the HTTP collection because Postman handles websocket testing separately. Use Postman’s WebSocket tab or another socket client if you want to test real-time chat.

## Suggested Test Order

1. `System > Health Check`
2. `Authentication > Login` or `Authentication > Register Company`
3. `Authentication > Me`
4. Test tenant-scoped folders such as `Employees`, `Departments`, `Documents`, and `Notifications`
5. Use create responses to populate IDs such as `department_id`, `document_id`, `subscription_id`, `request_id`, and `ticket_id`

## Troubleshooting

- If requests return `401`, confirm `access_token` is set and not expired.
- If requests return `403`, check the role required by that endpoint.
- If file uploads fail, confirm the request body is `form-data`, not raw JSON.
- If tenant requests fail, make sure `company_id` matches the token owner’s company.
- If a request still returns `500`, check whether the API service is up and whether the target record exists in PostgreSQL or MongoDB before retrying.