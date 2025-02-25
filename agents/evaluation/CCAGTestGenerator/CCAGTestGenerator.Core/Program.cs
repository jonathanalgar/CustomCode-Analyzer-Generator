namespace CCAGTestGenerator.Core
{
    /// <summary>
    /// Provides the main entry point for the CCAGTestGenerator CLI tool,
    /// dispatching to different commands based on command-line flags.
    /// </summary>
    public static class Program
    {
        /// <summary>
        /// Entry point of the application. Determines which command to execute
        /// (test generation, report, class name extraction, param mapping, or addicon)
        /// based on arguments.
        /// </summary>
        /// <param name="args">CLI arguments passed to the program.</param>
        public static async Task Main(string[] args)
        {
            if (args.Length < 2)
            {
                PrintUsage();
                return;
            }

            try
            {
                switch (args[0].ToLowerInvariant())
                {
                    case "--report":
                        await Commands.ReportCommand.Execute(args);
                        break;
                    case "--map":
                        await Commands.MapCommand.Execute(args);
                        break;
                    case "--addicon":
                        await Commands.AddIconCommand.Execute(args);
                        break;
                    case "--classname":
                        await Commands.ClassNameCommand.Execute(args);
                        break;
                    default:
                        // If no known flag is provided, assume test generation mode by default
                        await Commands.GenerateTestsCommand.Execute(args);
                        break;
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error: {ex.Message}");
                Environment.Exit(1);
            }
        }

        /// <summary>
        /// Prints usage instructions to the console if the user does not provide enough arguments.
        /// </summary>
        private static void PrintUsage()
        {
            Console.WriteLine("Usage:");
            Console.WriteLine(
                "  CCAGTestGenerator <source-file> <test-cases-yaml> [--paramMap <mapping-string>]"
            );
            Console.WriteLine("  CCAGTestGenerator --report <source-file> <test-cases-yaml>");
            Console.WriteLine("  CCAGTestGenerator --classname <source-file>");
            Console.WriteLine("  CCAGTestGenerator --map <source-file>");
            Console.WriteLine("  CCAGTestGenerator --addicon <source-file> <icon-filename>");
        }
    }
}
