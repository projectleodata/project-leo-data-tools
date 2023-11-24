# Project LEO Data Tools

Project LEO intended to create impact beyond its research and operation boundaries and all our tools have been developed with open-source software, access, and use in mind. Though tools were aimed towards Project LEO partners, with specific needs being met, the design of our tools can be implemented in a wide range of projects and the code has been made available through our data repositories post-project.

Dash by Plotly is a unique suite of open-source libraries that have allowed us at Project LEO to build user-friendly and highly interactive data cleaning tools. Dash strips away the gritty code running the data cleaning, allowing a completely unfamiliar user the ability to clean their data from anywhere and through their web browser of choice. In Project LEO, we have built these tools for both internal and external stakeholders to easily access. The packages and open-sourced libraries running in the backend were hosted using Heroku, enabling users at the time the ability to access these tools through a URL. Previous tools such as the Time Syncing Tool were built on Jupyter Notebooks, but the use of this tool is not inherently obvious to the average user as much of the code running the analysis is ‘exposed’ and needs to be configured. Furthermore, the need and use of this tool with Project LEO did not warrant migration to a Dash web-based application.

In essence, the Project LEO GitHub contains the source code for all of our data tools whereby data users and fast-followers (project catalysing on the work of Project LEO and others) can explore ways in which they can bring this functionality to their project needs. The only data tool (internal) that is not listed on the GitHub repository is the Project LEO Power BI Database which allowed internal partners the ability to explore aspects of data management. However, this was built on Power BI and thus does not have source code, but further information on its development can be seen in the Relevant Reports found in the post-project database.

***Important Notice: These tools retain the code that was used during the project and have been left deliberately as to show various functionality and formatting options. They will however need customising in order to create new data tools.***


## About These Tools

These data tools were meant for partner use within Project LEO but have been designed with open-access functionality in mind post-LEO, thus affording fast-followers and other interested stakeholders the opportunity to access energy and data tools that will address shared issues in local energy markets and systems.


### Time-Sync Tool

An internal-specific tool that allows partners the ability to explore monitoring data to correct and time-syncing issues that may occur between the substation and asset-specific metering data. This tool was one of the first and was built in a Jupyter Notebook, demonstrating how these interactive coding platforms can be used internally to provide ease of use in solving more difficult problems.


### Data Cleaning Tool

A tool for the cleaning of timeseries power data whereby missing data were discovered and treated with various solutions. This tool relied on Dash by Plotly and was hosted on Heroku (free hosting) and was the first tool to show how seemingly complex web-based applications can be made in a very user-friendly, open-access tool.


### Health Scan Tool

Like the Data Cleaning Tool, this tool was more used for the discovery of errors to aid users in preparing their datasets themselves before sharing internally or uploading to the Data Cleaning Tool for further processing. This tool was also built on Dash and hosted on Heroku.


### Bid Analysis Tool 

One of our most widely used tools was an internal tool that allowed partners to better understand various bidding strategies for DSO-issued flex services and the impact on their profit margins. This very comprehensive tool (built and hosted like the previous tools) demonstrates how previous Excel-constrained tools can bring more interactivity and engagement through web-based applications.



## License

Distributed under the MIT License. See `LICENSE.txt` for more information.

<p align="right">(<a href="#top">back to top</a>)</p>



<!-- CONTACT --> 
## Contact

[David Wallom](mailto:david.wallom@eng.ox.ac.uk) is the Data Controller of these tools should you need further information.

<p align="right">(<a href="#top">back to top</a>)</p>
