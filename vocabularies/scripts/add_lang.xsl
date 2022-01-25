<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.1"
                xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
                xmlns:skos="http://www.w3.org/2004/02/skos/core#"
                xmlns:xlink="http://www.w3.org/1999/xlink"
                xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
>

    <!-- ================================================================= -->
    <xsl:output method="xml" omit-xml-declaration="yes" indent="yes"/>

    <xsl:template match="node()">
        <xsl:copy>
            <xsl:apply-templates select="@*|node()"/>
        </xsl:copy>
    </xsl:template>

    <xsl:template match="@*">
        <xsl:copy/>
    </xsl:template>

    <xsl:template match="*[skos:prefLabel/@xml:lang='en']">
        <xsl:copy>
            <xsl:apply-templates select="@*|node()"/>

            <xsl:call-template name="addLang">
                <xsl:with-param name="lang" select="'it'"/>
                <xsl:with-param name="default_text" select="skos:prefLabel[@xml:lang='en']/text()"/>
            </xsl:call-template>
            <xsl:call-template name="addLang">
                <xsl:with-param name="lang" select="'de'"/>
                <xsl:with-param name="default_text" select="skos:prefLabel[@xml:lang='en']/text()"/>
            </xsl:call-template>
            <xsl:call-template name="addLang">
                <xsl:with-param name="lang" select="'fr'"/>
                <xsl:with-param name="default_text" select="skos:prefLabel[@xml:lang='en']/text()"/>
            </xsl:call-template>
            <xsl:call-template name="addLang">
                <xsl:with-param name="lang" select="'es'"/>
                <xsl:with-param name="default_text" select="skos:prefLabel[@xml:lang='en']/text()"/>
            </xsl:call-template>

        </xsl:copy>
    </xsl:template>


    <xsl:template name="addLang">
        <xsl:param name="lang"/>
        <xsl:param name="default_text"/>

        <xsl:if test='count(skos:prefLabel[@xml:lang=$lang])=0'>
            <skos:prefLabel xml:lang="{$lang}"><xsl:value-of select="$default_text"/></skos:prefLabel>
        </xsl:if>
    </xsl:template>

</xsl:stylesheet>
