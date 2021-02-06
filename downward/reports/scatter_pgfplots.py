import logging
import os.path

from lab import tools


class ScatterPgfplots:
    @classmethod
    def _get_plot(cls, report):
        lines = []
        options = cls._get_axis_options(report)
        if report.x_upper is not None:
            options["xmax"] = report.x_upper
        if report.y_upper is not None:
            options["ymax"] = report.y_upper
        lines.append(f"\\begin{{axis}}[{cls._format_options(options)}]")
        for category, coords in sorted(report.categories.items()):
            lines.append(
                "\\addplot+[{}] coordinates {{\n{}\n}};".format(
                    cls._format_options({"only marks": True}),
                    " ".join(str(c) for c in coords),
                )
            )
            if category:
                lines.append(f"\\addlegendentry{{{category}}}")
            elif report.has_multiple_categories():
                # None is treated as the default category if using multiple
                # categories. Add a corresponding entry to the legend.
                lines.append("\\addlegendentry{default}")

        if report.plot_horizontal_line:
            # Add black line at y=1.
            line_min, line_max = cls._get_supported_range(options["xmode"])
            lines.append(
                f"\\draw[color=black] (axis cs:{line_min},1) -- "
                f"(axis cs:{line_max},1);"
            )
        if report.plot_diagonal_line:
            # Add black diagonal line.
            assert options["xmode"] == options["ymode"]
            line_min, line_max = cls._get_supported_range(options["xmode"])
            lines.append(
                f"\\draw[color=black] (axis cs:{line_min},{line_min}) -- "
                f"(axis cs:{line_max},{line_max});"
            )

        lines.append("\\end{axis}")
        return lines

    @classmethod
    def _get_supported_range(cls, mode):
        # These are approximate values found by trial and error.
        if mode == "normal":
            return "-1e3", "1e3"
        else:
            assert mode == "log"
            return "1e-70", "1e70"

    @classmethod
    def write(cls, report, filename):
        lines = (
            [
                r"\documentclass[tikz]{standalone}",
                r"\usepackage{pgfplots}",
                r"\begin{document}",
                r"\begin{tikzpicture}",
            ]
            + cls._get_plot(report)
            + [r"\end{tikzpicture}", r"\end{document}"]
        )
        tools.makedirs(os.path.dirname(filename))
        tools.write_file(filename, "\n".join(lines))
        logging.info(f"Wrote file://{filename}")

    @classmethod
    def _get_axis_options(cls, report):
        axis = {}
        axis["xlabel"] = report.xlabel
        axis["ylabel"] = report.ylabel
        axis["title"] = report.title
        axis["legend cell align"] = "left"

        convert_scale = {"log": "log", "symlog": "log", "linear": "normal"}
        axis["xmode"] = convert_scale[report.xscale]
        axis["ymode"] = convert_scale[report.yscale]

        # Plot size is set in inches.
        figsize = report.matplotlib_options.get("figure.figsize")
        if figsize:
            width, height = figsize
            axis["width"] = f"{width:.2f}in"
            axis["height"] = f"{height:.2f}in"

        if report.has_multiple_categories():
            axis["legend style"] = cls._format_options(
                {"legend pos": "outer north east"}
            )

        return axis

    @classmethod
    def _format_options(cls, options):
        opts = []
        for key, value in sorted(options.items()):
            if value is None or value is False:
                continue
            if isinstance(value, bool) or value is None:
                opts.append(key)
            elif isinstance(value, str):
                if " " in value or "=" in value:
                    value = f"{{{value}}}"
                opts.append(f"{key}={value.replace('_', '-')}")
            else:
                opts.append(f"{key}={value}")
        return ", ".join(opts)
