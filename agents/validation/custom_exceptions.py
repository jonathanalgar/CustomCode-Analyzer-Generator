class ProjectSetupError(Exception):
    """Raised when project setup fails."""

    def __init__(self, message: str, output: str = ""):
        super().__init__(message)
        self.output = output


class PackageInstallationError(Exception):
    """Raised when a NuGet package installation fails."""

    def __init__(self, package: str, error_output: str):
        self.package = package
        self.error_output = error_output
        super().__init__(f"Failed to install package {package}: {error_output}")
