import asyncio
import os
import shutil
import tempfile
import textwrap
from typing import Dict, List, Optional

# Add Docker SDK for Python
import docker
from docker.errors import DockerException

from src.tools.tool_decorator import tool


class CodeExecutionEnvironment:
    """Base class for code execution environments"""

    async def execute_code(
        self, code: str, timeout: int = 30
    ) -> Dict[str, str]:
        """Execute code and return results"""
        raise NotImplementedError

    async def execute_project(
        self,
        project_files: Dict[str, str],
        main_file: str,
        install_deps: bool = False,
        requirements: Optional[List[str]] = None,
        timeout: int = 60,
    ) -> Dict[str, str]:
        """Execute a project and return results"""
        raise NotImplementedError


class SubprocessExecutionEnvironment(CodeExecutionEnvironment):
    """Execute code using subprocess (fallback method)"""

    async def run_process(
        self, cmd: List[str], cwd: Optional[str] = None, timeout: int = 30
    ) -> Dict[str, str]:
        """
        Run a subprocess with timeout and return stdout, stderr and return code.

        Args:
            cmd: Command to run as a list of strings
            cwd: Current working directory for the process
            timeout: Maximum execution time in seconds

        Returns:
            Dict containing stdout, stderr and return_code
        """
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout
                )
                return {
                    "stdout": stdout.decode("utf-8", errors="replace"),
                    "stderr": stderr.decode("utf-8", errors="replace"),
                    "return_code": process.returncode,
                }
            except asyncio.TimeoutError:
                try:
                    process.kill()
                except:
                    pass
                return {
                    "stdout": "",
                    "stderr": f"Execution timed out after {timeout} seconds",
                    "return_code": -1,
                }
        except Exception as e:
            return {
                "stdout": "",
                "stderr": f"Error executing command: {str(e)}",
                "return_code": -1,
            }

    async def execute_code(
        self, code: str, timeout: int = 30
    ) -> Dict[str, str]:
        """
        Execute a Python code snippet using subprocess.

        Args:
            code: The Python code to execute
            timeout: Maximum execution time in seconds

        Returns:
            Dict containing stdout, stderr and return_code
        """
        # Create a temporary file to hold the code
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as tmp:
            tmp_path = tmp.name
            tmp.write(textwrap.dedent(code).encode("utf-8"))

        try:
            # Execute the code in a subprocess
            return await self.run_process(["python", tmp_path], timeout=timeout)
        finally:
            # Clean up the temporary file
            try:
                os.unlink(tmp_path)
            except:
                pass

    async def execute_project(
        self,
        project_files: Dict[str, str],
        main_file: str,
        install_deps: bool = False,
        requirements: Optional[List[str]] = None,
        timeout: int = 60,
    ) -> Dict[str, str]:
        """
        Execute a multi-file Python project using subprocess.

        Args:
            project_files: Dictionary mapping file paths to file contents
            main_file: The main file to execute
            install_deps: Whether to install dependencies
            requirements: List of pip requirements to install
            timeout: Maximum execution time in seconds

        Returns:
            Dict containing stdout, stderr and return_code
        """
        # Create a temporary directory for the project
        temp_dir = tempfile.mkdtemp()

        try:
            # Write all project files
            for file_path, content in project_files.items():
                # Handle possible directory structure in the path
                full_path = os.path.join(temp_dir, file_path)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)

                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(textwrap.dedent(content))

            # Install dependencies if requested
            if install_deps and requirements:
                # Create requirements.txt
                req_path = os.path.join(temp_dir, "requirements.txt")
                with open(req_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(requirements))

                # Install dependencies
                pip_result = await self.run_process(
                    ["pip", "install", "-r", "requirements.txt"],
                    cwd=temp_dir,
                    timeout=60,  # Give pip installation a generous timeout
                )

                if pip_result["return_code"] != 0:
                    return pip_result

            # Execute the main file
            main_path = os.path.join(temp_dir, main_file)
            if not os.path.exists(main_path):
                return {
                    "stdout": "",
                    "stderr": f"Error: Main file '{main_file}' does not exist in project files.",
                    "return_code": -1,
                }

            return await self.run_process(
                ["python", main_path], cwd=temp_dir, timeout=timeout
            )
        finally:
            # Clean up the temporary directory
            try:
                shutil.rmtree(temp_dir)
            except:
                pass


class DockerExecutionEnvironment(CodeExecutionEnvironment):
    """Execute code using Docker containers for isolation"""

    def __init__(
        self,
        image: str = "python:3.11-slim",
        network_disabled: bool = True,
        memory_limit: str = "512m",
        cpu_limit: float = 1.0,
    ):
        """
        Initialize the Docker execution environment.

        Args:
            image: Docker image to use
            network_disabled: Whether to disable network access
            memory_limit: Memory limit for the container
            cpu_limit: CPU limit for the container (cores)
        """
        self.image = image
        self.network_disabled = network_disabled
        self.memory_limit = memory_limit
        self.cpu_limit = cpu_limit

        # Initialize Docker client
        try:
            self.client = docker.from_env()
            # Check if Docker is available by listing containers
            self.client.containers.list(limit=1)
            self.docker_available = True
        except (DockerException, ImportError):
            self.docker_available = False
            print("Docker not available. Falling back to subprocess execution.")
            # Initialize fallback execution environment
            self.fallback = SubprocessExecutionEnvironment()

    async def execute_code(
        self, code: str, timeout: int = 30
    ) -> Dict[str, str]:
        """
        Execute a Python code snippet in a Docker container.

        Args:
            code: The Python code to execute
            timeout: Maximum execution time in seconds

        Returns:
            Dict containing stdout, stderr and return_code
        """
        if not self.docker_available:
            print("Docker not available. Using subprocess fallback.")
            return await self.fallback.execute_code(code, timeout)

        # Create a temporary file to hold the code
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as tmp:
            tmp_path = tmp.name
            tmp.write(textwrap.dedent(code).encode("utf-8"))

        try:
            # Prepare container configuration
            volumes = {
                os.path.abspath(tmp_path): {
                    "bind": "/code/script.py",
                    "mode": "ro",  # Read-only
                }
            }

            # Create and run container
            container = self.client.containers.run(
                self.image,
                ["python", "/code/script.py"],
                volumes=volumes,
                network_disabled=self.network_disabled,
                mem_limit=self.memory_limit,
                cpu_period=100000,  # Default period
                cpu_quota=int(
                    self.cpu_limit * 100000
                ),  # Quota relative to period
                detach=True,  # Run in background
            )

            try:
                # Wait for container to finish or timeout
                result = container.wait(timeout=timeout)
                logs = container.logs(stdout=True, stderr=True)

                # Split stdout and stderr (Docker combines them)
                # In this simplified version, we'll treat all logs as stdout
                return {
                    "stdout": logs.decode("utf-8", errors="replace"),
                    "stderr": "",
                    "return_code": result["StatusCode"],
                }
            except Exception as e:
                # Handle timeout or other errors
                try:
                    container.kill()
                except:
                    pass
                return {
                    "stdout": "",
                    "stderr": f"Execution error: {str(e)}",
                    "return_code": -1,
                }
            finally:
                # Always remove the container
                try:
                    container.remove(force=True)
                except:
                    pass
        finally:
            # Clean up the temporary file
            try:
                os.unlink(tmp_path)
            except:
                pass

    async def execute_project(
        self,
        project_files: Dict[str, str],
        main_file: str,
        install_deps: bool = False,
        requirements: Optional[List[str]] = None,
        timeout: int = 60,
    ) -> Dict[str, str]:
        """
        Execute a multi-file Python project in a Docker container.

        Args:
            project_files: Dictionary mapping file paths to file contents
            main_file: The main file to execute
            install_deps: Whether to install dependencies
            requirements: List of pip requirements to install
            timeout: Maximum execution time in seconds

        Returns:
            Dict containing stdout, stderr and return_code
        """
        if not self.docker_available:
            print("Docker not available. Using subprocess fallback.")
            return await self.fallback.execute_project(
                project_files, main_file, install_deps, requirements, timeout
            )

        # Create a temporary directory for the project
        temp_dir = tempfile.mkdtemp()

        try:
            # Write all project files
            for file_path, content in project_files.items():
                # Handle possible directory structure in the path
                full_path = os.path.join(temp_dir, file_path)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)

                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(textwrap.dedent(content))

            # Create Dockerfile for custom dependencies if needed
            if install_deps and requirements:
                # Create requirements.txt
                req_path = os.path.join(temp_dir, "requirements.txt")
                with open(req_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(requirements))

                # Create a Dockerfile that installs the requirements
                dockerfile_path = os.path.join(temp_dir, "Dockerfile")
                with open(dockerfile_path, "w", encoding="utf-8") as f:
                    f.write(
                        f"""
                    FROM {self.image}
                    WORKDIR /app
                    COPY requirements.txt /app/
                    RUN pip install --no-cache-dir -r requirements.txt
                    COPY . /app/
                    CMD ["python", "{main_file}"]
                    """
                    )

                # Build a custom image with requirements
                custom_image_tag = (
                    f"code_execution_temp:{os.path.basename(temp_dir)}"
                )
                try:
                    self.client.images.build(
                        path=temp_dir, tag=custom_image_tag, rm=True
                    )
                    image_to_use = custom_image_tag
                except Exception as e:
                    return {
                        "stdout": "",
                        "stderr": f"Error building Docker image with requirements: {str(e)}",
                        "return_code": -1,
                    }
            else:
                # Use the base image without custom requirements
                image_to_use = self.image

            # Prepare container configuration
            volumes = {
                os.path.abspath(temp_dir): {
                    "bind": "/app",
                    "mode": "ro",  # Read-only
                }
            }

            # Create and run container
            cmd = (
                ["python", f"/app/{main_file}"]
                if not (install_deps and requirements)
                else None
            )
            container = self.client.containers.run(
                image_to_use,
                cmd,
                volumes=(
                    volumes if not (install_deps and requirements) else None
                ),
                working_dir="/app",
                network_disabled=self.network_disabled,
                mem_limit=self.memory_limit,
                cpu_period=100000,
                cpu_quota=int(self.cpu_limit * 100000),
                detach=True,
            )

            try:
                # Wait for container to finish or timeout
                result = container.wait(timeout=timeout)
                logs = container.logs(stdout=True, stderr=True)

                return {
                    "stdout": logs.decode("utf-8", errors="replace"),
                    "stderr": "",
                    "return_code": result["StatusCode"],
                }
            except Exception as e:
                # Handle timeout or other errors
                try:
                    container.kill()
                except:
                    pass
                return {
                    "stdout": "",
                    "stderr": f"Execution error: {str(e)}",
                    "return_code": -1,
                }
            finally:
                # Always remove the container
                try:
                    container.remove(force=True)
                except:
                    pass

                # Remove custom image if created
                if install_deps and requirements:
                    try:
                        self.client.images.remove(image_to_use, force=True)
                    except:
                        pass
        finally:
            # Clean up the temporary directory
            try:
                shutil.rmtree(temp_dir)
            except:
                pass


# Create a default execution environment (Docker with subprocess fallback)
execution_environment = DockerExecutionEnvironment()


@tool()
async def execute_code(code: str, timeout: int = 30) -> str:
    """
    Execute a Python code snippet in a sandboxed environment.

    Args:
        code: The Python code to execute
        timeout: Maximum execution time in seconds

    Returns:
        str: The execution result, including stdout, stderr, and return code
    """
    result = await execution_environment.execute_code(code, timeout)

    # Format the result
    if result["return_code"] == 0:
        if result["stdout"]:
            return f"Execution successful:\n{result['stdout']}"
        else:
            return "Execution successful with no output."
    else:
        return f"Execution failed (return code {result['return_code']}):\n{result['stderr']}"


@tool()
async def execute_project(
    project_files: Dict[str, str],
    main_file: str,
    install_deps: bool = False,
    requirements: Optional[List[str]] = None,
    timeout: int = 60,
) -> str:
    """
    Execute a multi-file Python project in a sandboxed environment.

    Args:
        project_files: Dictionary mapping file paths to file contents
        main_file: The main file to execute
        install_deps: Whether to install dependencies
        requirements: List of pip requirements to install
        timeout: Maximum execution time in seconds

    Returns:
        str: The execution result, including stdout, stderr, and return code
    """
    result = await execution_environment.execute_project(
        project_files, main_file, install_deps, requirements, timeout
    )

    # Format the result
    if result["return_code"] == 0:
        if result["stdout"]:
            return f"Execution successful:\n{result['stdout']}"
        else:
            return "Execution successful with no output."
    else:
        return f"Execution failed (return code {result['return_code']}):\n{result['stderr']}"
