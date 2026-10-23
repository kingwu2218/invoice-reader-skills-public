# Field-level ending-dash processor cases, v3

Synthetic supplied transcriptions, not visual recognition or live user replies. Authored before execution; never generated from processor predictions. All amounts retain `125-` in raw/custom values.

The invoice has a computer-generated total, handwritten unit price and computer-generated line total despite its document-wide handwriting flag. The cheque amount is handwritten. The statement debit is handwritten but its balance has unknown origin. Auto must convert only the handwritten amounts. Two separately labelled scripted replies resolve only invoice Total, once positive and once negative. Other values and review flags stay unchanged; incomplete arithmetic stays Not checkable.

The runner also retains v1 explicit modes and tests absent metadata against the unchanged v1 unknown reference. These checks measure conversion of supplied text/metadata. They cannot measure whether a model correctly identifies handwriting or asks the user.
