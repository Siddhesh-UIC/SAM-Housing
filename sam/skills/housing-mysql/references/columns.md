# housing_data column reference

All amounts DECIMAL(15,2) INR. Dates are DATE. Blocked for sam_agent: AAdharNo, Co_Applicant_AdharNo, Co_Applicant_PAN, PanNo.

## Core columns

`BusinessUnit`, `STATUS`, `Provisional`, `BookingNo`, `BookingDate`, `ApplicationNo`, `ApplicationDate`, `CustomerName`, `MobileNo1`, `MobileNo2`, `EmailId1`, `EmailId2`, `BookingRemarks`, `CustomerNameWithRelation`, `Co_Applicant_Name`, `Co_Applicant_Name_With_Relation`, `UnitCode`, `Floor`, `Agreementdate`, `Allotmentdate`, `CancelDate`, `HierarchyLebel`, `Level4`, `Level3`, `Level2`, `Level1`, `Rate1`, `Rate2`, `Rate3`, `PaymentPlan`, `SalesPersonName`, `SuperBuiltup`, `Builtup`, `Carpet`, `LandUDS`, `NewArea`, `OldArea`, `diffArea`, `AgreementRegistrationNo`, `AgreementRegistrationDate`, `CRoName`, `TotalBasicWithoutTax`, `TotalBasicWithTax`, `TotalBillWithoutTax`, `TotalBilledWithtTax`, `TotalPaidWithoutTax`, `TotalPaidWithtTax`, `TotalOutstandingWithoutTax`, `TotalOutstandingWithtTax`, `TotalOnAccountAmountWithoutTax`, `TotalOnAccountAmountWithtTax`, `TotalAdhocBillWithoutTax`, `TotalAdhocBillWithTax`, `TotalAdhocPaidWithoutTax`, `TotalAdhocPaidWithtTax`, `TotalDiscount`, `LatePaymentFeeAccrued`, `LatePaymentFeeWaived`, `LatePaymentFeePaid`, `NetLatePaymentFeeAccrued`, `Bookingid`

## Charge-head columns

Pattern: `` `<head>_<metric>` `` — always backtick (names start with a digit).

| Head | Meaning |
|---|---|
| `001_Unit_Charge` | Basic sale price of the unit |
| `002_Extra_Charge` | Extra charges |
| `003_Other_Charge` | Other charges |
| `004_Extra_Charge_Maintenance` | Maintenance deposit / charges |
| `005_Other_Charge_Non_Revenue` | Non-revenue charges |
| `006_Extra_Charge_Other` | Other miscellaneous charges |

Metrics: `BasicAmount` (contract value), `BillAmount` (demanded so far), `ReceivedAmount` (paid), `BalanceAmount` (due), `OnAccountAmount` (unadjusted). Each also has a `...Tax` twin with the GST part.

Example: `` SELECT `001_Unit_Charge_BalanceAmount`, `001_Unit_Charge_BalanceAmountTax` FROM housing_data WHERE BookingNo = '...'; ``
