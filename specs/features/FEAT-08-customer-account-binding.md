# Feature: Customer Account Binding
**Owner:** Backend | **Module:** Ticket Management

## Goal
Guarantee every ticket is linked to the customer who created it.

## Scope
- Read `customer_id` from the verified JWT (`sub` claim) — never trust a customer id sent in the request body.
- Store `customer_id` as a foreign key on the `tickets` table.
