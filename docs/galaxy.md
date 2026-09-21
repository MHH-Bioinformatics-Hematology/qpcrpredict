# Galaxy

The Galaxy tool **MRD-PCR predictor** wraps `qpcrpredict predict`. Running the prediction in Galaxy
documents every call: the history records the input run file, the tool version, all parameters and
the output table, and the call can be repeated or built into a workflow.

## Installation

Install the tool `qpcrpredict` (owner `mhh-hematology`) from the Galaxy ToolShed through the administrator
interface. All dependencies are resolved from the Bioconda package or the corresponding BioContainer.

## Upload

Upload the `.eds` or RDML file to a history. Galaxy has no dedicated datatype for these formats;
both are ZIP archives. If the datatype is not detected as `binary` or `zip`, set it in the dataset
attributes.

## Parameters

| Parameter | Description |
|---|---|
| qPCR run file | An `.eds` or RDML file from the history. The format is detected from the content. |
| Assay | The packaged AML MRD assay, or an assay configuration (JSON) from the history. |
| Target | With the packaged assay one of `NPM1`, `RUNX1::RUNX1T1`, `CBFB::MYH11`, `PML::RARA`, `BCR::ABL1`; with your own assay a target name or the detector name on the plate. |
| Prediction model | **Packaged default model**, or **Trained model from history** to select a model bundle (`.pkl`) that was created with `qpcrpredict train` and uploaded to the history. |
| Single sample id (optional) | Score only this sample. Leave empty to score all samples of the target. |

## Output

One tabular dataset with the columns described in [Output](output.md). The console report is available
in the tool's standard output.

## Workflows

A plate with two targets is handled with two tool steps on the same input dataset, one per target.
Because the output is a plain table, it can be filtered with the standard text tools, for example
to extract all rows with `decision` equal to `review` or `na`.

Training is not part of the Galaxy tool. Train a model on the command line and upload the
resulting bundle. Upload only bundles from a source you trust, see [Training](train.md).

## Integration into a laboratory workflow

In the setup described in the publication, the instrument computer is isolated in a private
network. A router computer forwards each finished run file to the compute side, where the Galaxy
tool is called through the Galaxy API. The output table is then available to a laboratory
information management system for review and approval.
