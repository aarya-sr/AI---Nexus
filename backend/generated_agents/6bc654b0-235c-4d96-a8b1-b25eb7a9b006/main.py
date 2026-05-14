from orchestration import create_crew

def main():
    crew = create_crew()
    result = crew.kickoff(inputs={})
    import json
    print(json.dumps({"result": result.raw}, indent=2))

if __name__ == "__main__":
    main()
