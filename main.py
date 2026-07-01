import asyncio
from app import download, command_manager


async def _async_main():
    """Parse arguments and run the download."""
    args = command_manager()
    await download(args)


def main():
    """CLI entry point: run the async download pipeline."""
    try:
        asyncio.run(_async_main())
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
