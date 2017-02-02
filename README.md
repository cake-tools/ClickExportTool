# CAKE Click Export Tool

**THE CLICK EXPORT TOOL MUST BE USED ON Python 2.7**

In order to run the CAKE Click Export Tool, you will need to follow the directions below:

## Requirements
* `Python 2.7`
* `MongoDB`
* `AWS SQS`
* `AWS S3`

## Guidelines
  * Please use Python 2.7 to run the Click Export Tool!
  * This tool is not meant for LARGE date ranges or LARGE report sizes. Whenever possible, please keep your report queries in one day intervals maximum. Remember, you have the ability to queue multiple jobs!
  * Please consider that it may take hours to complete one queued job.
  * Use the format 'dd-mm-yyyy' for both the start and end date (the dashes must be included)
  * **Do not use the Clicks Export Tool concurrently with the Conversion Export Tool. This can cause one or both of the Export Tools to time out and fail.**
  * Create a new SQS queue and a new S3 bucket for your click reports. Please make sure that the appropriate credentials and names are added to `settings.py`


## Instructions

1. First execute the following command in your terminal `pip install -r requirements.txt`. This will install all the necessary Python packages to run the tool.

2. Configure your AWS credentials
  * In your terminal run `aws config`. It will ask you a few questions requiring you to provide an AWS access key and secret key as well as your default region.

3. Fill in each empty quote in `settings.py`
	* If you are using the Conversion Export Tool, make sure that your SQS queue and S3 buckets are different from those used in the Conversion Export Tool.

4. Run the web interface
  * In the main cake click tools directory, run the command 'python run.py', this starts the Flask web server for the web interface.
  * Navigate to "http://localhost:5000"
  * Log into the interface using your admin domain address (without 'http://'), and an email address and password for a user that has admin access in your CAKE instance.

Once your credentials are validated, you will land on the welcome page, which will allow you to queue report exports.

5. Scheduling a Click Report Export:
  * Fill in the start and end date, being mindful of the date format 'dd-mm-yyyy' (the dashes must be included)
  * Click "Schedule Job"
  * When the job is successfully added to the queue, the message 'job has been scheduled' will appear underneath the grey well.
  * If you want to schedule multiple jobs, just add another start and end date combo.

Great! You've scheduled an export. Now in a separate terminal window, navigate to the project and run the command 'python task_runner.py'. The script repeats every minute to check if there are new jobs in the queue and subsequently processes those. Keep 'task_runner.py' open for the duration of the export job.

The Task Runner connects to the SQS queue and processes each job in the queue, sequentially. The Click Export Tool divides one day's export into 24 separate csv's, one for each hour of the day. Please keep in mind that it may take a few hours to complete a one day report.

The Click Export Tool does not display a 'Download Report' link in the web interface due to the volume of csv's generated. Your csv's are available for download in your respective S3 bucket.

## Additional Information

### How the Click Export Tool Works

The Click Export Tool executes a series api calls, each one exporting 5 minutes worth of Click Report data. At the end of each hour, the csv is uploaded to S3. Each filename in S3 uses the following format, consisting of 4 parts:

`ClickReport_10012016_0000_0100`

1. Report Title: all reports are titled `ClickReport`
2. Date of Exported Data: If you requested click data from January 10th 2016, the date is written `10012016` or `DDMMYYYY` format.
3. Start Hour: Beginning hour of report
4. End Hour: Ending hour of report



### Reading Your Queue Report (Web Interface)


#### Job Statuses
Your queued export job can have one of the following statuses:
* `Queued`: Your job was successfully added to the SQS queue. When the task runner is executed, it will read from the SQS queue and process each queue item in the order that it was entered.
* `In Progress`: Your queued job is now being actively exported. In this state, it is best to leave your task runner alive until you receive an updated status.
* `Success`: Your queue job has completed. The `Download Link` is now visible. Clicking on the link will automatically start a download of your file.
* `Failed`: Your queue job encountered an error while being exported. Try reading the task runner output, or queue the job once again.

## FAQ

**Q: My report has started processing, but it is now frozen on the same interval for a long period of time. What can I do?**

A: Follow these steps:
* Cancel the `task_runner.py`.
* Go to the Click Export Tool interface and requeue the job.
* Run the `task_runner.py` again.

**Q: I've successfully added an export job in the queue, but when I run `task_runner.py` I get either get an error or a "No Message in Queue" message.**

A: There is usually a short delay period between the time a message is sent to your SQS queue and when you can receive a message to process. Please wait one minute and run `task_runner.py` again to resolve this issue.

**Q: I received the following error message when running `task_runner.py`:**

        Traceback (most recent call last):
          File "task_runner.py", line 426, in <module>
            execute_call(response)
          File "task_runner.py", line 125, in execute_call
            body = (response["Messages"][0]["Body"]).replace("'", "\"")
        KeyError: 'Messages'

A: Please wait a few minutes, or manually go into the AWS SQS console and poll your queue. After, run `task_runner.py` again.
