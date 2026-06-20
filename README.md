![](../../workflows/gds/badge.svg) ![](../../workflows/docs/badge.svg) ![](../../workflows/test/badge.svg) ![](../../workflows/fpga/badge.svg)

## Welcome to UWASIC!

We are a University of Waterloo design team that makes ASICs (application-specific integrated circuits).

Please read the [documentation](https://docs.uwasic.com/s/onboarding) first.

Happy coding!

## Set up your Verilog project

1. Edit the [info.yaml](info.yaml) and update information about your project, paying special attention to the `source_files` and `top_module` properties.
2. Edit [docs/info.md](docs/info.md) and add a description of your project.
3. Add your Verilog files to the `src` folder.
4. Edit [test/Makefile](test/Makefile) and modify `PROJECT_SOURCES` to point to your Verilog files.
5. Edit [test/tb.v](test/tb.v) and replace `tt_um_example` with your module name.
