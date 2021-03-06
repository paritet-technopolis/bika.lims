# This file is part of Bika LIMS
#
# Copyright 2011-2016 by it's authors.
# Some rights reserved. See LICENSE.txt, AUTHORS.txt.

""" Shimadzu ICPE-9000 Multitype
"""
from DateTime import DateTime
from Products.Archetypes.event import ObjectInitializedEvent
from Products.CMFCore.utils import getToolByName
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from bika.lims import bikaMessageFactory as _
from bika.lims.utils import t
from bika.lims import logger
from bika.lims.browser import BrowserView
from bika.lims.idserver import renameAfterCreation
from bika.lims.utils import changeWorkflowState
from bika.lims.utils import tmpID
from cStringIO import StringIO
from datetime import datetime
from operator import itemgetter
from plone.i18n.normalizer.interfaces import IIDNormalizer
from zope.component import getUtility
import csv
import json
import plone
import re
import zope
import zope.event
from bika.lims.exportimport.instruments.resultsimport import InstrumentCSVResultsFileParser,\
    AnalysisResultsImporter
import traceback

title = "Shimadzu ICPE-9000 Multitype"


def Import(context, request):
    """ Read Shimadzu GICPE-9000 Multitype analysis results
    """
    form = request.form
    #TODO form['file'] sometimes returns a list
    infile = form['file'][0] if isinstance(form['file'],list) else form['file']
    artoapply = form['artoapply']
    override = form['override']
    sample = form.get('sample', 'requestid')
    instrument = form.get('instrument', None)
    errors = []
    logs = []

    # Load the most suitable parser according to file extension/options/etc...
    parser = None
    if not hasattr(infile, 'filename'):
        errors.append(_("No file selected"))
    parser = ICPEMultitypeCSVParser(infile)

    if parser:
        # Load the importer
        status = ['sample_received', 'attachment_due', 'to_be_verified']
        if artoapply == 'received':
            status = ['sample_received']
        elif artoapply == 'received_tobeverified':
            status = ['sample_received', 'attachment_due', 'to_be_verified']

        over = [False, False]
        if override == 'nooverride':
            over = [False, False]
        elif override == 'override':
            over = [True, False]
        elif override == 'overrideempty':
            over = [True, True]

        sam = ['getRequestID', 'getSampleID', 'getClientSampleID']
        if sample =='requestid':
            sam = ['getRequestID']
        if sample == 'sampleid':
            sam = ['getSampleID']
        elif sample == 'clientsid':
            sam = ['getClientSampleID']
        elif sample == 'sample_clientsid':
            sam = ['getSampleID', 'getClientSampleID']

        importer = ICPEMultitypeImporter(parser=parser,
                                           context=context,
                                           idsearchcriteria=sam,
                                           allowed_ar_states=status,
                                           allowed_analysis_states=None,
                                           override=over,
                                           instrument_uid=instrument)
        tbex = ''
        try:
            importer.process()
        except:
            tbex = traceback.format_exc()
        errors = importer.errors
        logs = importer.logs
        warns = importer.warns
        if tbex:
            errors.append(tbex)

    results = {'errors': errors, 'log': logs, 'warns': warns}

    return json.dumps(results)


class ICPEMultitypeCSVParser(InstrumentCSVResultsFileParser):

    QUANTITATIONRESULTS_NUMERICHEADERS = ('Title8', 'Title9','Title31',
            'Title32','Title41', 'Title42','Title43', 
            )
    def __init__(self, csv):
        InstrumentCSVResultsFileParser.__init__(self, csv)
        self._end_header = False
        self._quantitationresultsheader = []
        self._numline = 0

    def _parseline(self, line):
        return self.parse_resultsline(line)

    def parse_resultsline(self, line):
        """ Parses result lines
        """

        # Metals Mix Method with IS longer cali\tCAL1\tBlank\t9/23/2016 11:54:59 AM\t\tMRC\tAs\tQUANT\t193.759\t1\tppb\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\tAfter Drift Correction\t-0.0936625\t-0.1063610\t-0.1266098\t\t\t\t\t\t\t\t-0.1088778\t0.0166172\t15.26

        splitted = [token.strip() for token in line.split('\t')]
        quantitation = {'DefaultResult': 'Title8'}
        # File has no headers
        self._quantitationresultsheader  = ['Title%s' % x for x in range(44)]
        for colname in self._quantitationresultsheader:
            quantitation[colname] = ''

        for i in range(len(splitted)):
            token = splitted[i]
            if i < len(self._quantitationresultsheader):
                colname = self._quantitationresultsheader[i]
                if colname in self.QUANTITATIONRESULTS_NUMERICHEADERS:
                    try:
                        quantitation[colname] = float(token)
                    except ValueError:
                        self.warn(
                            "No valid number ${token} in column ${index} (${column_name})",
                            mapping={"token": token,
                                     "index": str(i + 1),
                                     "column_name": colname},
                            numline=self._numline, line=line)
                        quantitation[colname] = token
                elif colname == 'Title3':
                    d = datetime.strptime(token, "%m/%d/%Y %I:%M:%S %p")
                    quantitation[colname] = d
                else:
                    quantitation[colname] = token

            elif token:
                self.err("Orphan value in column ${index} (${token})",
                         mapping={"index": str(i+1),
                                  "token": token},
                         numline=self._numline, line=line)

        val = re.sub(r"\W", "", splitted[6])
        self._addRawResult(quantitation['Title2'],
                           values={val:quantitation},
                           override=True)

class ICPEMultitypeImporter(AnalysisResultsImporter):

    def __init__(self, parser, context, idsearchcriteria, override,
                 allowed_ar_states=None, allowed_analysis_states=None,
                 instrument_uid=''):
        AnalysisResultsImporter.__init__(self, parser, context, idsearchcriteria,
                                         override, allowed_ar_states,
                                         allowed_analysis_states,
                                         instrument_uid)
