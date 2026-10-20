# SOFTWARE REQUIREMENTS SPECIFICATION

## Stokari — Offline-First Inventory and Sales Management Application

**Document Version:** 0.5
**Document Status:** Revised Draft — Decisions Incorporated
**Date:** October 13, 2026
**Project Type:** Student Software Engineering Project
**Team Size:** 4 members
**Planned Development Duration:** 4 weeks
**Contingency Plan:** 3-week reduced-scope delivery
**Target Market:** Small retailers in Ethiopia
**Primary Interface:** Responsive Progressive Web Application (PWA)
**Research Basis:** Secondary research; primary user validation remains necessary

---

# Document Control

## Revision History

| Version | Description |
|---|---|
| 0.1–0.3 | Earlier requirements drafts. |
| 0.4 | Revised requirements, including offline operation, synchronization states, and explicit offline-data indicators. |
| 0.5 | Resolved the 32 previously identified open decisions and clarified inventory integrity, synchronization, authentication, numeric rules, data recovery, and release priorities. |

## Purpose of This Revision

Version 0.5 converts previously open questions into explicit product requirements and business rules. These decisions provide a stable baseline for the Software Design Description (SDD).

The decisions in this document are selected design constraints for the MVP. They are not evidence that the assumptions have already been validated with real shop owners.

## Reference Standard

ISO/IEC/IEEE 29148:2018, *Systems and software engineering — Life cycle processes — Requirements engineering*.

This document follows a structured SRS approach informed by the standard. Formal compliance has not been independently audited.

---

# 1. Introduction

## 1.1 Purpose

Stokari is an offline-first inventory and sales management application intended for small Ethiopian retailers who currently depend on paper notebooks, spreadsheets, or informal record-keeping practices.

The application will allow shop owners and authorized attendants to manage products, record sales, track stock movements, and review business activity. Core operations must remain usable during internet interruptions.

When connectivity returns, the application will synchronize locally stored records with the server so that authorized members of the same shop can share business data.

## 1.2 Problem Statement

Small retailers may experience difficulties maintaining accurate stock and sales records when internet connectivity is unreliable, several people work in the same shop, or transactions are recorded manually.

Stokari aims to reduce these problems by providing persistent local storage, explicit synchronization status, and controlled reconciliation of conflicting records.

The problem statement is based on secondary research and has not yet been validated through a completed primary-research study.
oject Objectives

Stokari shall:

1. Support product, sales, and stock management with intermittent or unavailable internet connectivity.
2. Preserve locally confirmed transactions across normal application restarts and unexpected closures.
3. Synchronize business records between authorized devices without silently duplicating their effects.
4. detect and expose inventory discrepancies caused by concurrent offline activity.
5. Enforce owner and attendant permissions on the server.
6. Communicate whether information is local, synchronized, stale, or awaiting review.
7. Remain practical to build, test, and demonstrate within four weeks.

## 1.4 Scope

### In scope

- Shop registration and authentication.
- Owner and attendant roles.
- Product creation, editing, deactivation, and search.
- Sales and payment-method labels.
## 1.3 Pr
- Stock receipts and adjustments.
- Append-only stock movement history.
- Offline data persistence.
- Synchronization and retry handling.
- Multi-device conflict detection and owner review.
- Dashboard and inventory valuation.
- Explicit connectivity and data-freshness indicators.
- Basic export and backup-related safeguards.

### Out of scope for the MVP

- Payment processing or payment settlement.
- Integration with Telebirr or other payment-provider APIs.
- Supplier procurement and automated purchasing.
- Payroll and employee attendance.
- Accounting, tax filing, and statutory financial reporting.
- Multi-branch inventory management.
- Automatic resolution of every inventory conflict.
- A dedicated native Android application.
- Guaranteed recovery of data that existed only on a lost device and was never exported or synchronized.
- Self-service shop ownership transfer.
- Full offline identity verification independent of the device's previous authorization.

## 1.5 Definitions

| Term                        | Definition                                                                                                                      |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| Owner                       | The user with authority over shop settings, staff, stock adjustments, and conflict resolution.                                  |
| Attendant                   | An authorized user who can perform permitted operational tasks, including recording sales.                                      |
| Platform administrator      | A platform-level operator who manages platform administration, not ordinary shop transactions.                                  |
| Server-confirmed stock      | Stock calculated from stock-affecting events accepted by the server.                                                            |
| Local projected stock       | A device's locally calculated stock after applying eligible local operations, including pending transactions.                   |
| Pending operation           | A locally persisted operation that has not received definitive server acceptance.                                               |
| Stock movement              | An auditable event that changes stock, such as a receipt, sale, cancellation, or adjustment.                                    |
| Conflict                    | A condition in which concurrent or stale operations cannot be reconciled safely without additional review.                      |
| Idempotency key             | A unique identifier that prevents a retried operation from being applied more than once.                                        |
| Offline authorization lease | A time-limited server-issued authorization allowing a previously authenticated device to continue specified operations offline. |
| RPO                         | Recovery Point Objective: the maximum targeted amount of data loss after a server disaster.                                     |
| RTO                         | Recovery Time Objective: the target time to restore service after a server disaster.                                            |

---

# 2. Overall Description

## 2.1 Product Perspective

Stokari will be a responsive PWA supported by a backend API and a central database.

The PWA will store necessary application resources and pending business operations locally. The server will provide shared shop data, centralized authorization, durable transaction acceptance, and synchronization coordination.

The application will not treat local data as automatically synchronized simply because it has been saved on a device.

## 2.2 User Roles

| Role | Principal permissions |
|---|---|
| Owner | Manage products, invite and deactivate attendants, view business summaries, receive stock, adjust stock, cancel eligible sales, resolve conflicts, export data, and manage shop settings. |
| Attendant | Search products, record sales, view permitted stock information, and perform explicitly authorized operational tasks. Cannot manage users, change owner-only cost information, or resolve owner-only conflicts. |
| Platform administrator | Perform platform administration and audited support actions. Cannot automatically access or modify a shop's business records without an authorized, logged administrative procedure. |

The default maximum number of attendants per shop is five. This is configurable only if the project explicitly expands the scope.

## 2.3 Operating Environment

- Responsive PWA for supported Android and desktop browsers.
- Android Chrome as the primary mobile target.
- Desktop Chrome and Microsoft Edge as supported desktop targets.
- Local persistence using IndexedDB or an equivalent browser-supported transactional database.
- HTTPS for production communication.
- Central server API and relational database.
- EAT (UTC+3) for displayed business timestamps.
- ETB as the default currency.

The exact browser baseline will be the current stable release and the preceding major release of supported browsers at release time, subject to compatibility testing. The earlier Chrome 90 baseline is not retained.

## 2.4 Core Product Principles

1. **Persist before confirming:** A transaction is not reported as saved unless it has been durably persisted locally or accepted by the server.
2. **Preserve business events:** A completed real-world sale must not silently disappear because synchronization later detects a conflict.
3. **Separate saving from synchronization:** Local persistence and server acceptance are distinct states.
4. **Do not duplicate stock effects:** Retrying an operation must not apply its inventory effect more than once.
5. **Make uncertainty visible:** Stale data, pending changes, and conflicts must be clearly communicated.
6. **Enforce authorization on the server:** Hiding a button is not an authorization mechanism.
7. **Keep the MVP bounded:** Advanced functionality must not displace the Must requirements.

## 2.5 Assumptions and Constraints

- The MVP is intended for small retailers rather than large warehouse operations.
- Users may experience long periods without reliable internet access.
- Users may operate multiple devices within the same shop.
- Browser storage is not equivalent to a server backup.
- A lost device can permanently lose records that existed only on that device.
- Offline revocation cannot take effect immediately on a disconnected device.
- The four-week schedule is the baseline; the three-week plan is a reduced-scope contingency.
- Product-name availability and target-user assumptions remain to be verified.

---

# 3. Functional Requirements

Priority definitions:

- **Must:** Required for MVP acceptance.
- **Should:** Implement if time and resources permit without compromising Must requirements.
- **Could:** Optional future enhancement.

## 3.1 Shop, Identity, and Permissions

### FR-01 — Shop Registration
**Priority: Must**

The system shall allow an eligible user to create a shop with a unique identifier and required shop details. Shop creation shall establish the user as the shop owner.

### FR-02 — Authentication
**Priority: Must**

The MVP shall use Google OpenID Connect through a maintained authentication library.

The system shall validate authentication responses on the server. Password-based authentication and SMS-based authentication are excluded from the MVP.

Before release, the team should validate that Google-account access is practical for the intended users. If primary research shows this assumption is unacceptable, the team must revise the requirements rather than silently introduce another authentication method.

### FR-03 — Attendant Invitations
**Priority: Must**

The owner shall be able to invite attendants to the shop, subject to the default maximum of five attendants.

An attendant shall not gain access to a shop until the invitation is accepted and server-side membership is established.

### FR-04 — Attendant Deactivation
**Priority: Must**

The owner shall be able to deactivate an attendant.

When the server learns of the deactivation, it shall reject new requests from that attendant and revoke active online authorization.

Pending records shall be preserved for audit and reconciliation. Records associated with a valid offline authorization lease may be submitted for validation, but deactivation shall not automatically guarantee acceptance of every pending record.

Operations created without valid authorization, or operations that cannot be attributed or validated safely, shall be marked for owner review or rejected with an auditable reason.

### FR-05 — Role-Based Permissions
**Priority: Must**

The server shall enforce role and shop-membership permissions for every protected operation and sensitive data field.

Attendants shall not access owner-only cost information, manage memberships, perform owner-only stock adjustments, or resolve conflicts requiring owner authority.

### FR-06 — Sessions and Offline Authorization
**Priority: Must**

The normal server-authenticated session shall have a maximum lifetime of 30 days, subject to the authentication provider's policies.

The application shall use a server-issued offline authorization lease with a maximum validity of seven days from its issuance or renewal.

While a lease remains valid, the device may perform explicitly permitted offline operations. Once the lease expires, the application shall permit read-only access to available local data but shall not allow new protected business operations until authorization is renewed.

The server shall validate lease identifiers, membership, operation types, record integrity, and synchronization policy. Client timestamps alone shall not establish authorization.

The seven-day lease limits offline exposure but cannot guarantee immediate revocation on a disconnected device.

### FR-07 — Shop Data Isolation
**Priority: Must**

All shop-owned records shall be scoped to the authenticated user's authorized shop membership.

The server shall derive or validate shop access from authenticated membership and shall not trust a client-supplied shop identifier as proof of authorization.

Cross-shop access attempts shall be rejected and covered by automated tests.

---

## 3.2 Product and Inventory Management

### FR-08 — Product Creation
**Priority: Must**

The owner shall be able to create a product with a name, unit of measure, selling price, and opening stock quantity.

Where cost price is supported, it shall be restricted to the owner.

Product creation and opening-stock initialization shall be handled as a consistent operation so that the product is not left with an unintended stock balance.

### FR-09 — Product Editing and Deactivation
**Priority: Must**

The owner shall be able to edit product details and deactivate products.

Deactivation shall prevent new sales from being initiated against the product once the device knows it is inactive. A stale offline device may still contain the previously active product; such a sale shall be preserved locally and evaluated during synchronization.

Historical transactions shall retain their original product identity, unit, quantity, and price snapshots even after the product is edited or deactivated.

### FR-10 — Product Search
**Priority: Must**

The application shall support product search in English and Amharic product names where those names have been entered.

For a shop with up to 2,000 products, search shall return results in under one second under the defined test conditions.

### FR-11 — Input Validation
**Priority: Must**

The application and server shall validate required fields, numeric limits, quantity precision, price ranges, and operation-specific constraints.

Client-side validation shall improve usability but shall not replace server-side validation.

### FR-12 — Sales
**Priority: Must**

Authorized users shall be able to record a sale containing one or more product lines.

Each sale shall include a unique transaction identifier, product identifiers, quantity, unit of measure, unit-price snapshot, line totals, sale total, payment-method label, creation metadata, and synchronization status.

The payment-method labels shall be Cash, Telebirr, and Other. These labels record the method reported by the user; Stokari shall not process or verify payment settlement.

For a product already found in the local catalogue, the normal sale flow should require no more than three additional taps and complete in ten seconds or less under the defined usability-test conditions.

### FR-13 — Atomic Sale Processing
**Priority: Must**

A multi-product sale shall be processed as one atomic business transaction on the server.

The server shall not apply some sale lines while silently excluding other lines from the same sale.

The sale record shall preserve the transaction as a whole. Its stock effects shall be applied exactly once according to the conflict rules in Section 4.

### FR-14 — Idempotent Operations
**Priority: Must**

Every operation submitted for synchronization shall have a globally unique operation identifier or an equivalent idempotency key.

The server shall persist the operation's outcome and return the same definitive outcome when the same operation is retried.

Retries shall not create duplicate sales, duplicate stock movements, or duplicate cancellation effects.

### FR-15 — Overselling and Inventory Conflicts
**Priority: Must**

The server shall prevent ordinary online sales from reducing available stock below zero.

Offline sales may cause a concurrent overselling discrepancy because another device may sell the same stock before synchronization. The system shall preserve both completed sale records and identify the discrepancy for owner review.

The system shall not silently discard the second sale or pretend the physical transaction never happened.

Until the discrepancy is resolved, affected inventory shall be marked as requiring review, and the application shall block additional online sales that would worsen the negative or uncertain stock balance.

### FR-16 — Sale Cancellation
**Priority: Must**

Only the owner may cancel a sale.

Cancellation shall create an auditable compensating operation rather than deleting or rewriting the original sale. The compensating stock movement shall be applied at most once.

An offline cancellation shall be stored as a pending operation and shall not be presented as server-confirmed until accepted.

A cancellation that conflicts with subsequent stock activity shall be preserved and flagged for owner review.

### FR-17 — Stock Receipts
**Priority: Must**

The owner shall be able to record incoming stock.

A receipt shall contain a unique identifier, product, quantity, timestamp, actor, and optional cost information.

Cost information shall be accessible only to authorized owners. Receipt creation and its stock effect shall be atomic and idempotent.

### FR-18 — Stock Adjustments
**Priority: Must**

The owner shall be able to record stock adjustments using one of these reasons:

- DAMAGE
- LOSS
- CORRECTION
- OTHER

Each adjustment shall include a quantity change, reason, actor, timestamp, and optional explanatory note.

Adjustments shall create append-only stock movement records. Existing stock history shall not be silently rewritten.

### FR-19 — Low-Stock Indicator
**Priority: Must**

The application shall indicate when a product's stock is at or below its configured low-stock threshold.

When local projected stock differs from server-confirmed stock, the interface shall identify the displayed value as local or pending rather than presenting it as fully synchronized.

### FR-20 — Stock History
**Priority: Must**

The system shall maintain a chronological, auditable stock movement history for receipts, sales, cancellations, adjustments, and conflict resolutions.

Each stock-affecting event shall be traceable to its source operation and actor where applicable.

### FR-21 — Physical Stock Counts
**Priority: Should**

If implemented, physical stock counts shall record the observed quantity and count time.

The system shall not blindly overwrite stock with a count taken before later sales or receipts. A count shall be reconciled against movements that occurred after the count began.

The owner shall approve the resulting adjustment.

---

## 3.3 Offline Operation and Synchronization

### FR-22 — Core Offline Availability
**Priority: Must**

The application shall allow authorized users with a valid offline authorization lease to perform supported core operations without an internet connection.

At minimum, users shall be able to search locally available products and record sales. Other supported offline operations shall follow the role and operation policies defined in the SDD.

### FR-23 — Durable Local Persistence
**Priority: Must**

A business operation shall be committed to local persistent storage before the interface reports it as saved on the device.

If local persistence fails, the application shall show a clear error and shall not claim that the transaction was saved.

Local persistence shall use transactions or equivalent atomic mechanisms to prevent partially written sales.

### FR-24 — Record and Connectivity States
**Priority: Must**

Each record shall use a defined synchronization state, as appropriate:

- Waiting to sync
- Syncing
- Synced
- Needs review
- Rejected

The application shall separately show the overall connectivity and synchronization condition, such as:

- Offline
- Syncing
- Up to date
- Attention required

A locally saved record shall not be labelled `Synced` until the server has durably accepted it and returned a definitive acknowledgment.

Rejected records shall remain available for inspection or export unless the owner explicitly removes them under the data-retention policy.

### FR-25 — Automatic Synchronization
**Priority: Must**

While the application is active and connectivity is available, it shall attempt to synchronize eligible pending operations automatically, targeting initiation within 30 seconds.

Failed requests shall be retried with exponential backoff and jitter. Retrying shall not duplicate server-side effects.

The application shall not promise a 30-second synchronization guarantee when the device is offline, suspended, or unable to run background work.

### FR-26 — Synchronization Integrity
**Priority: Must**

The system shall be tested with at least two devices, each generating up to 100 offline records before reconnecting.

Synchronization shall preserve all locally confirmed records, avoid duplicate transaction identifiers and stock effects, and explicitly report operations requiring review.

### FR-27 — Conflict Resolution
**Priority: Must**

The server shall detect conflicts involving concurrent sales, receipts, adjustments, cancellations, product deactivation, and other operations that cannot be safely applied according to current server state.

The original business records shall be preserved. Conflicts shall include a reason, affected records, the relevant server state, and the required owner action.

The owner shall be able to resolve supported conflicts through an explicit, auditable operation. Resolution shall not modify historical records silently.

### FR-28 — Offline Application Launch
**Priority: Must**

After the application has been installed or successfully loaded at least once, the cached application shell shall be available offline on supported browsers, subject to browser storage and platform limitations.

The interface shall explain when data cannot be refreshed because the device is offline.

### FR-29 — Shared-Shop Mode
**Priority: Must**

The default shop mode shall be shared mode, in which eligible business data is synchronized to the server and made available to authorized shop members.

The application shall display the last successful synchronization time when known and shall distinguish shared server-confirmed data from local pending changes.

### FR-30 — Local-Only Shop Mode
**Priority: Should**

If implemented, local-only mode shall clearly explain that the shop's data remains on that device and is not shared with other devices through the server.

The application shall distinguish local-only records from shared-shop records. It shall not silently convert a local-only shop into a shared shop or merge data without an explicit migration procedure.

### FR-37 — Explicit Offline and Local-Data Indicator
**Priority: Must**

The application shall maintain a visible connectivity and data-status indicator on primary business screens.

When offline, the interface shall communicate that it is using data saved on the device and that changes will synchronize when internet access returns.

When pending or conflicting records exist, the interface shall indicate that shared data may be incomplete or inconsistent until synchronization and review are completed.

Suggested baseline wording:

- **Offline:** “Offline — using data saved on this device. Changes will sync when internet returns.”
- **Syncing:** “Syncing changes…”
- **Up to date:** “Up to date — last synced [time].”
- **Needs review:** “Some changes need owner review. Shop devices may show different totals until resolved.”
- **Local-only mode:** “Local-only shop — data stays on this device and is not shared with other devices.”

Final wording may be refined during usability testing, but the meaning must remain explicit.

---

## 3.4 Dashboard, Export, and Localization

### FR-31 — Dashboard
**Priority: Must**

The dashboard shall display sales and stock summaries based on available records.

The dashboard shall distinguish server-confirmed results from local projections when pending or conflicting operations could materially affect the displayed totals.

### FR-32 — Inventory Valuation
**Priority: Must**

Only the owner may access inventory cost information and inventory valuation.

Valuation shall use the latest known eligible cost data and shall identify when pending or unresolved inventory movements make the figure incomplete or approximate.

The system shall not present an uncertain local projection as an exact, server-confirmed valuation.

### FR-33 — Data Export
**Priority: Should**

The application should allow owners to export supported business records to CSV.

The export should include enough identifiers and timestamps to distinguish transactions and reconcile them with stock history.

The application should also provide a way to export pending local records in a documented machine-readable format, such as JSON, with a clear warning that exported data may contain sensitive business information.

### FR-34 — Currency and Time
**Priority: Must**

The default currency shall be Ethiopian birr (ETB).

Server timestamps shall be stored in UTC and displayed in East Africa Time (EAT, UTC+3) where appropriate.

The system shall not rely on the device's displayed local time alone for authorization or server acceptance.

### FR-35 — Amharic and English Interface
**Priority: Should**

The interface should support Amharic and English. Product names shall support the languages independently of the selected interface language.

### FR-36 — Ethiopian Calendar
**Priority: Could**

Ethiopian calendar display may be added if time permits. Gregorian timestamps shall remain available for unambiguous record identification and technical reconciliation.

---

# 4. Binding Business Rules for Inventory and Synchronization

This section resolves the most consequential inventory decisions and shall guide the SDD, data model, and implementation.

## 4.1 Server-Authoritative Stock

The server shall maintain the authoritative record of accepted shared-shop stock movements.

Each device shall calculate its local projected stock from:

1. The latest known server-confirmed stock state.
2. Eligible local stock-affecting operations not yet confirmed by the server.
3. Known conflict and review states.

The implementation shall prevent an operation from being included twice when it transitions from local pending status to server-confirmed status.

The interface may show both server-confirmed stock and local projected stock when they differ. The local projected quantity shall be explicitly labelled.

## 4.2 Stock Calculation

For a product, the basic balance is:

**Stock balance = opening stock + accepted receipts + accepted adjustments − accepted sales + accepted cancellation reversals.**

This formula is conceptual. The actual implementation shall derive the balance from the stock movement ledger or a transactionally maintained balance that can be reconciled against that ledger.

Every stock movement shall have a unique identifier and a reference to its originating operation.

## 4.3 Offline Overselling Example

Initial server-confirmed stock: 10 units.

- Device A completes a sale of 7 units while offline.
- Device B completes a sale of 6 units while offline.
- Both sales are durably saved on their respective devices.
- Both devices later synchronize.

The system shall:

1. Preserve both sale records because both represent completed real-world transactions.
2. Process the synchronization operations idempotently.
3. Detect that the combined sales exceed the available stock.
4. Apply the documented conflict policy and flag the resulting stock discrepancy.
5. Prevent further ordinary online sales against an invalid or negative available balance.
6. Notify the owner and require an explicit reconciliation or adjustment.
7. Record the resolution as a new auditable operation.

The system shall not delete either sale or silently alter its quantity to make the balance appear valid.

Negative or uncertain stock is not a normal permitted online selling condition. It may appear as a temporary discrepancy caused by offline concurrency or other confirmed real-world events and must be visibly flagged.

## 4.4 Atomic Multi-Product Sales

A sale containing multiple products shall be one business transaction.

The server shall validate the sale and its stock effects within a transaction boundary. It shall not apply only the lines that happen to pass validation while silently dropping the others.

If the sale cannot be reconciled safely, the sale shall be preserved as a whole and its stock outcome shall be marked for review according to the conflict policy.

## 4.5 Operation Identity and Idempotency

Every sale, receipt, adjustment, cancellation, and conflict-resolution action shall have a stable unique operation identifier.

A synchronization retry using the same identifier shall return the stored result of the original operation.

The server shall prevent duplicate application of a stock movement even if a request times out after the transaction commits.

## 4.6 Synchronization Acknowledgment

A record shall transition to `Synced` only after the server confirms durable acceptance.

A successful HTTP response that does not confirm the operation's committed result is insufficient.

If a request times out and the device cannot determine whether the server committed it, the device shall retry with the same idempotency key or query the operation status. It shall not create a new operation identifier merely because the result is uncertain.

## 4.7 Owner Conflict Resolution

Conflict resolution shall be a separate, auditable operation.

When the owner resolves a conflict offline, the device shall persist the proposed resolution locally and mark it as pending. It shall not display the resolution as server-confirmed.

When connectivity returns, the server shall validate the resolution against the latest state. If the state has changed in a way that invalidates the resolution, the server shall return the conflict for further review.

## 4.8 Product Deactivation

A product deactivation shall prevent new online sales once accepted by the server.

A stale offline device may still contain the product in its local catalogue. A sale completed on that device shall be preserved as a pending business record and evaluated against the deactivation and authorization policies during synchronization.

The system shall not silently erase a sale because the product became inactive after the device last synchronized.

## 4.9 Cancellation and Stock Restoration

Cancellation shall not delete the original sale.

An accepted cancellation shall create a compensating stock movement exactly once. If a cancellation conflicts with subsequent movements or cannot be verified safely, the operation shall remain visible and require review.

## 4.10 Physical Stock Counts

If physical stock counts are implemented, the system shall record the count time and observed quantity.

Movements occurring after the count began shall be considered during reconciliation. A count shall not blindly replace the latest balance without accounting for those movements.

## 4.11 Dashboard Semantics

The dashboard shall follow these rules:

- Server-confirmed totals shall include only operations accepted by the server.
- Local projected totals may include eligible pending local operations and must be labelled as local.
- Operations marked `Needs review` shall be identified separately.
- The dashboard shall not silently count one operation both as pending and as confirmed.
- Inventory valuation shall disclose material uncertainty caused by pending or unresolved operations.
- In offline or stale conditions, the interface shall display the last successful synchronization time when available.

---

# 5. Authentication and Security Decisions

## 5.1 Google Authentication

Google OpenID Connect is the sole authentication method for the MVP.

The team shall validate this choice with target users before release. Adding phone OTP, password authentication, or another identity provider requires an explicit scope change.

## 5.2 Offline Authorization Lease

The server shall issue a time-limited offline authorization lease to a successfully authenticated device.

The lease shall identify the authorized user, shop membership, allowed offline operations, issue time, and expiry time.

The client shall not be trusted to extend the lease or declare that a lease remains valid after its expiry.

A disconnected device cannot receive immediate revocation information. This limitation shall be reflected in the threat model and user-facing documentation.

## 5.3 Deactivation and Pending Records

The server shall reject unauthorized new operations after it receives and applies deactivation.

Pending records shall be validated against the authorization and synchronization rules. The system shall preserve records for review when rejecting or withholding them is necessary to avoid silent data loss.

The client timestamp alone shall not establish that an operation was authorized before deactivation.

## 5.4 Account Recovery

Users shall use Google's account-recovery mechanisms to recover access to their Google account.

The MVP shall not provide an unaudited mechanism for bypassing Google authentication.

If an owner permanently loses access to their account, ownership transfer shall require a separately approved, audited administrative process. Self-service ownership transfer is excluded from the MVP.

## 5.5 Server-Side Authorization

The server shall validate user identity, shop membership, role, resource ownership, and operation permissions for every protected request.

Automated tests shall cover attempts to access another shop's products, sales, stock history, cost information, and administrative functions.

## 5.6 Sensitive Local Data

The application shall avoid storing authentication secrets unnecessarily in browser-accessible storage.

The application shall minimize locally stored sensitive data, and the design shall document the limitations of browser-based offline storage, especially on shared or lost devices.

---

# 6. Data and Numeric Rules

## 6.1 Quantity Precision

The MVP shall use a unit of measure defined for each product.

- Discrete units such as pieces and packs shall use whole-number quantities.
- Weight and volume units, when supported, shall permit up to three decimal places.
- Pack-to-piece conversion shall not be assumed unless an explicit conversion rule is defined for the product.

The server and client shall apply the same validation rules.

## 6.2 Numeric Limits

The initial MVP limits shall be:

| Field | Limit |
|---|---|
| Unit selling price | 0 to ETB 999,999,999.99 |
| Unit cost price | 0 to ETB 999,999,999.99 |
| Quantity | Up to 999,999.999, subject to the unit's precision rule |
| Stock adjustment | Up to the configured quantity limit, subject to validation against the resulting stock state |

These limits are product constraints selected for the MVP, not claims about typical retail transactions. They may be adjusted before implementation if testing identifies a practical need.

## 6.3 Monetary Precision and Rounding

Monetary values shall be stored and calculated using a representation that avoids binary floating-point errors.

The preferred representation is integer minor units (santim) for monetary amounts.

Unit prices shall be stored at two decimal places. For fractional quantities, each line total shall be rounded to two decimal places using a documented half-up rounding rule. The sale total shall be the sum of the rounded line totals.

The same calculation rules shall be used on the client and server. The server's validated result shall be authoritative for shared records.

## 6.4 Historical Price Snapshots

Each sale line shall preserve the unit price used when the sale was created, along with the product identifier, unit of measure, quantity, and calculated line total.

Later product-price changes shall not rewrite historical sale values.

Where a sale was created offline using a stale price, the original completed transaction shall be preserved. The system shall apply the documented conflict policy rather than silently replacing its price with the latest catalogue price.

---

# 7. Data Lifecycle, Retention, and Recovery

## 7.1 Shop Closure and Deletion

The MVP shall support a controlled shop-closure process rather than immediate destructive deletion.

Before closure, the owner shall be warned about unsynchronized records and encouraged to synchronize and export available business data.

A closed shop shall be disabled for new ordinary operations. The server shall retain its business records for five years after closure as the initial product-retention policy, subject to later legal and privacy review.

At the end of the retention period, records shall be deleted or anonymized according to the approved retention procedure.

## 7.2 Ownership Transfer

Self-service ownership transfer is out of scope.

If an ownership transfer becomes necessary, it shall use an audited administrative procedure with documented verification. The old owner's access shall be revoked as part of the approved transfer.

## 7.3 Local Data Loss

Browser storage can be cleared, evicted, corrupted, or lost with the device.

The application shall not promise recovery of unsynchronized records that existed only on a lost device.

The application shall warn users that pending local records are not yet backed up by the server. Where supported, owners should be able to export pending records before clearing or replacing a device.

The system shall not imply that a remote server can erase data from a device that remains offline.

## 7.4 Backup Policy

The server shall target:

- Daily backups.
- Fourteen-day backup retention.
- A maximum target RPO of 24 hours for server-side disaster recovery.
- A target RTO of 24 hours for restoration of core service.
- At least one documented restore test before release.

These are service objectives for the MVP, not guarantees against every possible failure.

The backup process shall be tested for actual restoration rather than judged only by successful backup-job completion.

## 7.5 Data Export

CSV export is a Should feature for synchronized business records.

A separate local export mechanism for unsynchronized records should be provided where feasible. The export shall be clearly labelled, include operation identifiers and status information, and warn users to protect the resulting file because it may contain sensitive business data.

---

# 8. Nonfunctional Requirements

## 8.1 Performance

| ID | Requirement |
|---|---|
| NFR-01 | Common local business actions should complete within 300 ms at the 95th percentile under defined test conditions. |
| NFR-02 | A previously cached application shell should launch in under three seconds under defined test conditions. |
| NFR-03 | Product search across 2,000 locally available products shall return results in under one second under defined test conditions. |
| NFR-04 | Synchronizing 200 representative sales should transfer less than 200 KB of application payload, excluding protocol overhead, unless measured data shows the target is impractical. |

## 8.2 Reliability and Data Integrity

| ID | Requirement |
|---|---|
| NFR-05 | After 50 forced application closures and 20 simulated power-loss or abrupt-shutdown scenarios, every locally confirmed record shall survive under the defined test environment. |
| NFR-06 | Two devices generating up to 100 offline records each shall not produce silently lost or duplicated transactions during synchronization tests. |
| NFR-07 | Stock movement records shall be traceable to their originating operations. |
| NFR-08 | Idempotency and conflict tests shall demonstrate that retries do not duplicate stock effects. |
| NFR-09 | Backup restoration shall be demonstrated at least once before release. |

## 8.3 Security

| ID | Requirement |
|---|---|
| NFR-10 | Production traffic shall use HTTPS. |
| NFR-11 | Shop isolation and role permissions shall be enforced server-side. |
| NFR-12 | Owner-only cost information shall not be disclosed to attendants through API responses or other application paths. |
| NFR-13 | Authentication, authorization, and conflict-resolution failures shall be handled without exposing secrets or unnecessary sensitive data. |

## 8.4 Usability and Accessibility

| ID | Requirement |
|---|---|
| NFR-14 | The interface shall remain usable at a viewport width of 320 pixels without horizontal page scrolling. |
| NFR-15 | Touch targets should be at least 44 by 44 CSS pixels where practical. |
| NFR-16 | At least five participants outside the development team should test the core workflows, with at least 80% completing the defined basic sale task on their first attempt. |
| NFR-17 | Offline, pending, synchronized, and conflict states shall be visually and textually distinguishable. |

## 8.5 Capacity and Maintainability

| ID | Requirement |
|---|---|
| NFR-18 | The application shall support at least 2,000 products per shop and 50,000 stock movement records per shop in the defined test environment. |
| NFR-19 | The compressed application bundle should not exceed 2 MB, excluding externally loaded resources and data, unless a documented and justified exception is approved. |
| NFR-20 | At least 70% automated test coverage shall be targeted for core stock, synchronization, and permission logic. Every Must requirement shall map to one or more verification cases. |

## 8.6 Availability

The initial deployment shall target 99% monthly server availability, excluding explicitly documented maintenance windows.

This is a deployment objective, not an unconditional guarantee of service availability.

---

# 9. External Interface Requirements

## 9.1 User Interface

The interface shall provide clear navigation for products, sales, stock history, and dashboard information.

The connectivity and data-status indicator shall be visible on primary business screens, not hidden exclusively in settings.

Error messages shall explain whether an operation was saved locally, accepted by the server, rejected, or left requiring review.

## 9.2 API Interface

The client shall communicate with the backend through authenticated API requests over HTTPS.

The API shall provide explicit operation identifiers, validation errors, synchronization outcomes, and conflict information.

The API design shall distinguish transport failure from business rejection and from an operation that was accepted but whose acknowledgment was not received by the client.

## 9.3 Local Persistence Interface

The client shall use a transactional local data store to persist business records and pending synchronization operations.

The implementation shall define schema versioning and a migration strategy for locally stored records. An application update shall not silently discard pending transactions.

---

# 10. Verification and Acceptance

## 10.1 Core Acceptance Tests

| Test ID | Scenario | Acceptance criterion |
|---|---|---|
| AT-01 | Record a sale online | Sale is accepted, and its stock effect is applied exactly once. |
| AT-02 | Record a sale offline | Sale is durably stored locally and clearly marked as pending. |
| AT-03 | Restart after local save | The saved pending sale remains available after restart. |
| AT-04 | Retry after uncertain network result | The same operation is not duplicated. |
| AT-05 | Synchronize two devices with non-conflicting sales | All records synchronize without duplication. |
| AT-06 | Initial stock 10; offline sales of 7 and 6 | Both sales remain preserved; the discrepancy is detected and made visible for owner review. |
| AT-07 | Multi-product sale with one conflicting line | The sale is not partially applied or silently truncated. |
| AT-08 | Cancel a sale | Original sale remains in history; compensating stock effect is applied at most once. |
| AT-09 | Deactivate an attendant | Subsequent unauthorized online operations are rejected. |
| AT-10 | Attempt cross-shop access | The server denies access and the test confirms isolation. |
| AT-11 | Expired offline lease | New protected offline operations are blocked; local records remain available for appropriate review and export. |
| AT-12 | Attendant requests cost data | Cost information is not returned by the API. |
| AT-13 | Display dashboard while offline | Local projection and synchronization status are clearly identified. |
| AT-14 | Clear or replace local storage | User-facing guidance does not falsely promise recovery of unsynchronized records. |
| AT-15 | Restore server backup | Core data is restored within the documented recovery target in the test environment. |
| AT-16 | Validate quantity and price rules | Invalid precision, out-of-range values, and inconsistent totals are rejected. |
| AT-17 | Product deactivation during offline operation | The stale-device transaction is preserved and evaluated under the conflict policy. |
| AT-18 | Physical count with later movements | If implemented, reconciliation accounts for movements after the count began. |
| AT-19 | Pending export | Export identifies local pending records and does not label them as server-confirmed. |
| AT-20 | Offline-state indicator | Users can distinguish offline, syncing, up-to-date, and needs-review states. |

## 10.2 Requirements Traceability

Every Must requirement shall map to at least one verification case before the SRS is approved for implementation.

The following is the minimum traceability format:

| Requirement ID | Design component | Verification case | Status |
|---|---|---|---|
| FR-13 | Sale processing and database transaction | AT-07 | To be mapped in the SDD |
| FR-14 | Idempotency mechanism | AT-04 | To be mapped in the SDD |
| FR-23 | Local persistence layer | AT-02, AT-03 | To be mapped in the SDD |
| FR-25 | Synchronization worker | AT-04, AT-05 | To be mapped in the SDD |
| FR-27 | Conflict-resolution service | AT-06, AT-07 | To be mapped in the SDD |
| FR-37 | Connectivity and status UI | AT-13, AT-20 | To be mapped in the SDD |

This table is a starting point. The complete traceability matrix shall include every Must requirement before implementation is considered ready.

---

# 11. Scope Priorities and Delivery Plan

## 11.1 Four-Week Baseline

The four-week plan is the intended development schedule.

The team shall prioritize, in order:

1. Data model, shop isolation, authentication, and core product management.
2. Sales, stock movement history, and transaction integrity.
3. Local persistence, synchronization, idempotency, and conflict handling.
4. Connectivity indicators, dashboard, verification, and release preparation.

The actual task breakdown shall be maintained in the project plan.

## 11.2 Three-Week Contingency

If only three weeks are available, the team shall reduce scope by deferring Should and Could features.

Recommended deferral order:

1. Ethiopian calendar support.
2. Local-only shop mode.
3. Physical stock counts.
4. CSV export enhancements.
5. Amharic interface localization, if user validation and project constraints permit deferral.

The team shall not silently remove Must requirements for atomic sales, local persistence, synchronization integrity, server-side authorization, conflict visibility, or the offline-data indicator.

The final scope reduction shall be documented and approved by the team.

## 11.3 User Validation

Before final release, the team should conduct a usability test with at least five participants outside the development team, ideally including actual small-shop owners or attendants.

The team shall validate:

- Whether Google authentication is practical for intended users.
- Whether the offline-state messages are understandable.
- Whether users understand pending versus synchronized records.
- Whether the sales workflow is sufficiently fast.
- Whether conflict-resolution messaging explains the required action.

The team shall not describe secondary research assumptions as proven user findings.

## 11.4 Product Name

“Stokari” remains the working project name. Its availability has not been verified.

The team shall check relevant naming and domain availability before public release. The name shall not be treated as legally cleared solely because it is used in this document.

---

# 12. Risks and Limitations

| Risk                                                    | Mitigation                                                                                                    |
| ------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| Concurrent offline sales create overselling             | Preserve transactions, detect discrepancies, and require explicit owner reconciliation.                       |
| Network timeout after server commit                     | Use idempotency keys and durable operation outcomes.                                                          |
| Browser storage is cleared or device is lost            | Warn about pending records and provide export where feasible; do not promise recovery of unsynchronized data. |
| Attendant is deactivated while offline                  | Use limited offline leases, validate records on synchronization, and communicate revocation limitations.      |
| Stale product information is used offline               | Preserve completed business events and evaluate them using explicit conflict rules.                           |
| Team exceeds the schedule                               | Defer Should and Could features without silently removing Must requirements.                                  |
| Google authentication excludes intended users           | Validate with target users before release and revise the requirements if necessary.                           |
| Backup jobs succeed but data cannot be restored         | Perform a documented restore test.                                                                            |
| Dashboard appears authoritative despite pending changes | Separate server-confirmed figures from local projections and display review status.                           |
| Client and server calculations differ                   | Share and test numeric precision, rounding, and validation rules.                                             |

---

# 13. Decisions Incorporated in Version 0.5

The following table records the selected resolution for each of the 32 previously open decisions.

| ID | Decision | Selected resolution |
|---|---|---|
| 1 | Concurrent offline sales | Preserve both sales; detect the overselling discrepancy; require owner review. |
| 2 | Stock calculation | Server-authoritative ledger plus a separately labelled local projection. |
| 3 | Multi-product conflicts | Treat each sale as one atomic transaction; never silently apply only some lines. |
| 4 | Receipts, adjustments, cancellations, counts | Use unique operations, auditable stock movements, idempotency, and explicit conflict rules. |
| 5 | Successful synchronization | Mark `Synced` only after durable server acknowledgment. |
| 6 | Offline conflict resolution | Store a separate pending resolution and validate it against the latest server state. |
| 7 | Authentication method | Google OpenID Connect for the MVP; validate practicality with target users. |
| 8 | Offline session expiry | Thirty-day normal session with a maximum seven-day offline authorization lease; read-only after lease expiry. |
| 9 | Attendant deactivation | Revoke online access immediately after server-side deactivation; preserve and validate pending records. |
| 10 | Reauthentication and pending records | Preserve local records; require renewed authorization for new protected operations and validate pending records before acceptance. |
| 11 | Shop and role authorization | Server-side authorization on every protected request and sensitive field. |
| 12 | Quantity precision | Whole numbers for discrete units; up to three decimal places for weight and volume. |
| 13 | Numeric limits | Set explicit MVP bounds for prices and quantities in Section 6. |
| 14 | Monetary rounding | Integer minor-unit representation; documented half-up rounding to two decimal places. |
| 15 | Negative stock | Block ordinary online overselling; expose and reconcile negative or uncertain balances caused by offline concurrency. |
| 16 | Inactive products | Preserve stale-device sales and evaluate them during synchronization. |
| 17 | Cancellation | Owner-only, auditable compensating operation; pending offline cancellation requires synchronization and validation. |
| 18 | Physical stock counts | Should feature; reconcile movements occurring after the count began. |
| 19 | Historical prices | Preserve immutable sale-line price and quantity snapshots. |
| 20 | Account recovery | Use Google's recovery process; no unaudited authentication bypass. |
| 21 | Ownership transfer | Exclude self-service transfer; permit only an audited administrative procedure if required. |
| 22 | Shop deletion | Controlled closure; retain business records under the stated retention policy. |
| 23 | Data retention | Retain records while active and for five years after closure, subject to legal and privacy review. |
| 24 | Unsynchronized data loss | Explicit warning and pending-record export where supported; no promise of recovering data from a lost device. |
| 25 | Backup recovery targets | Daily backups, 14-day retention, target RPO 24 hours, target RTO 24 hours, and a restore test. |
| 26 | Delivery schedule | Four-week baseline; three-week contingency defers Should and Could features. |
| 27 | Should-feature priority | Ethiopian calendar and local-only mode are early deferral candidates; preserve Must requirements. |
| 28 | Product name | Stokari remains provisional until availability checks are completed. |
| 29 | User validation | Test with at least five participants outside the development team; prioritize actual shop users where possible. |
| 30 | Browser baseline | Current and preceding major stable versions of the supported browsers at release time. |
| 31 | Dashboard semantics | Distinguish server-confirmed totals, local projections, pending operations, and unresolved conflicts. |
| 32 | Offline-state wording | Adopt explicit Offline, Syncing, Up to date, Needs review, and Local-only messages. |

---

# 14. Remaining Approval Conditions

Version 0.5 resolves the 32 previously identified questions at the requirements level. The following activities are still required before the team treats the requirements as fully baselined:

1. Review the offline authorization and revocation policy against the intended security level and the limitations of browser-based applications.
2. Validate Google authentication and the usability assumptions with target users.
3. Complete the requirements-to-test traceability matrix for every Must requirement.
4. Add the actual sources and URLs used in the secondary research.
5. Confirm that the numeric limits and five-year retention policy are acceptable for the project and target users.
6. Review the complete SRS with all four team members and record approval.
7. Carry the selected business rules into the Software Design Description, particularly the data model, transaction boundaries, synchronization protocol, and conflict-resolution workflow.

The design team shall not silently change these decisions during implementation. Any change that affects data integrity, security, scope, or acceptance criteria shall be recorded as a requirements change.

---

# 15. Conclusion

Stokari SRS v0.5 establishes the intended behavior of the MVP more precisely than version 0.4, particularly for offline persistence, multi-device synchronization, inventory conflicts, security, and data recovery.

The key product rule is that Stokari must preserve real business events while making uncertainty visible. Offline transactions cannot always be reconciled automatically, but they must not be silently lost, duplicated, or presented as fully synchronized when they are not.

This version is a revised draft ready for team review and for use as the baseline input to the Software Design Description. It should be approved only after the remaining conditions in Section 14 have been addressed or explicitly accepted by the team.

**End of Document**
