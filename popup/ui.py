

def popup_html(row):
    i = row
    institution_name = df['INSTNM'].iloc[i]
    institution_url = df['URL'].iloc[i]
    institution_type = df['CONTROL'].iloc[i]
    highest_degree = df['HIGHDEG'].iloc[i]
    city_state = df['CITY'].iloc[i] + ", " + df['STABBR'].iloc[i]
    admission_rate = df['ADM_RATE'].iloc[i]
    cost = df['COSTT4_A'].iloc[i]
    instate_tuit = df['TUITIONFEE_IN'].iloc[i]
    outstate_tuit = df['TUITIONFEE_OUT'].iloc[i]

    left_col_color = "#19a7bd"
    right_col_color = "#f2f0d3"

    html = """<!DOCTYPE html>
<html>
<head>
<h4 style="margin-bottom:10"; width="200px">{}</h4>""".format(institution_name) + """
</head>
    <table style="height: 126px; width: 350px;">
<tbody>
<tr>
<td style="background-color: """ + left_col_color + """;"><span style="color: #ffffff;">Institution Type</span></td>
<td style="width: 150px;background-color: """ + right_col_color + """;">{}</td>""".format(institution_type) + """
</tr>
<tr>
<td style="background-color: """ + left_col_color + """;"><span style="color: #ffffff;">Institution URL</span></td>
<td style="width: 150px;background-color: """ + right_col_color + """;">{}</td>""".format(institution_url) + """
</tr>
<tr>
<td style="background-color: """ + left_col_color + """;"><span style="color: #ffffff;">City and State</span></td>
<td style="width: 150px;background-color: """ + right_col_color + """;">{}</td>""".format(city_state) + """
</tr>
<tr>
<td style="background-color: """ + left_col_color + """;"><span style="color: #ffffff;">Highest Degree Awarded</span></td>
<td style="width: 150px;background-color: """ + right_col_color + """;">{}</td>""".format(highest_degree) + """
</tr>
<tr>
<td style="background-color: """ + left_col_color + """;"><span style="color: #ffffff;">Admission Rate</span></td>
<td style="width: 150px;background-color: """ + right_col_color + """;">{}</td>""".format(admission_rate) + """
</tr>
<tr>
<td style="background-color: """ + left_col_color + """;"><span style="color: #ffffff;">Annual Cost of Attendance $</span></td>
<td style="width: 150px;background-color: """ + right_col_color + """;">{}</td>""".format(cost) + """
</tr>
<tr>
<td style="background-color: """ + left_col_color + """;"><span style="color: #ffffff;">In-state Tuition $</span></td>
<td style="width: 150px;background-color: """ + right_col_color + """;">{}</td>""".format(instate_tuit) + """
</tr>
<tr>
<td style="background-color: """ + left_col_color + """;"><span style="color: #ffffff;">Out-of-state Tuition $</span></td>
<td style="width: 150px;background-color: """ + right_col_color + """;">{}</td>""".format(outstate_tuit) + """
</tr>
</tbody>
</table>
</html>
"""
    return html